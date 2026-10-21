from __future__ import annotations
import io
import os
import time

from fastapi import HTTPException, UploadFile, status

import config

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:
    pass


def _get_s3():
    if not config.S3_ENABLED:
        return None
    import services.s3_storage as _mod
    return _mod


def _read_with_limit(upload: UploadFile) -> bytes:
    ctype = (upload.content_type or "").lower()
    if not ctype.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Файл должен быть изображением")
    buf = bytearray()
    while True:
        chunk = upload.file.read(64 * 1024)
        if not chunk:
            break
        buf += chunk
        if len(buf) > config.UPLOAD_MAX_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Файл слишком большой (макс. {config.UPLOAD_MAX_BYTES // (1024 * 1024)} МБ)",
            )
    return bytes(buf)


def _process(buf: bytes, max_size: int | None) -> tuple[bytes, bool]:
    if max_size is None:
        return buf, True
    from PIL import Image

    try:
        img = Image.open(io.BytesIO(buf))
        img.load()
    except (OSError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось прочитать изображение: файл повреждён или формат не поддерживается. "
                   "Пересохраните фото как JPG или PNG и попробуйте снова",
        )

    has_alpha = img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info)

    if img.mode == "P":
        img = img.convert("RGBA")
    elif img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA" if has_alpha else "RGB")

    w, h = img.size
    longest = max(w, h)
    if longest > max_size:
        scale = max_size / longest
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)

    out = io.BytesIO()
    if has_alpha:
        img.save(out, format="PNG", optimize=True)
        return out.getvalue(), True
    else:
        img.save(out, format="JPEG", quality=85, optimize=True)
        return out.getvalue(), False


def save_upload(upload: UploadFile, prefix: str, max_size: int | None = None) -> str:
    buf = _read_with_limit(upload)
    processed, is_png = _process(buf, max_size)
    if max_size is not None:
        ext = "png" if is_png else "jpg"
    else:
        ext = os.path.splitext(upload.filename or "")[1].lower().lstrip(".") or "png"
    name = f"{prefix}_{int(time.time())}_{os.urandom(3).hex()}.{ext}"

    s3 = _get_s3()
    if s3 and prefix.startswith("report_"):
        vk_id = prefix.split("_")[1]
        content_type = "image/png" if is_png else "image/jpeg"
        return s3.upload_bytes(f"{vk_id}/{name}", processed, content_type)

    path = os.path.join(config.UPLOADS_DIR, name)
    with open(path, "wb") as fh:
        fh.write(processed)
    return f"/api/uploads/{name}"


def _read_raw(upload: UploadFile, limit: int, label: str) -> bytes:
    buf = bytearray()
    while True:
        chunk = upload.file.read(64 * 1024)
        if not chunk:
            break
        buf += chunk
        if len(buf) > limit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{label} слишком большой (макс. {limit // (1024 * 1024)} МБ)",
            )
    return bytes(buf)


def _save_raw(buf: bytes, upload: UploadFile, prefix: str, default_ext: str) -> str:
    ext = os.path.splitext(upload.filename or "")[1].lower().lstrip(".") or default_ext
    name = f"{prefix}_{int(time.time())}_{os.urandom(3).hex()}.{ext}"
    path = os.path.join(config.UPLOADS_DIR, name)
    with open(path, "wb") as fh:
        fh.write(buf)
    return f"/api/uploads/{name}"


def save_raw_image_upload(upload: UploadFile, prefix: str) -> str:
    """Картинка без пережатия — для анимаций (GIF/WebP), где обработка сломала бы кадры."""
    ctype = (upload.content_type or "").lower()
    if not ctype.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Файл должен быть изображением")
    buf = _read_raw(upload, config.UPLOAD_MAX_BYTES, "Файл")
    return _save_raw(buf, upload, prefix, "gif")


SILHOUETTE_MAX_SIZE = 512
SILHOUETTE_BG_MIN_CHANNEL = 200
SILHOUETTE_BG_TOLERANCE = 30
STRIP_MAGIC = (1, 2, 3)


def _has_alpha(img) -> bool:
    return img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info)


def _strip_edge_white(img):
    from collections import Counter

    from PIL import ImageDraw

    rgb = img.convert("RGB")
    w, h = rgb.size

    border = []
    for x in range(w):
        border.append(rgb.getpixel((x, 0)))
        border.append(rgb.getpixel((x, h - 1)))
    for y in range(h):
        border.append(rgb.getpixel((0, y)))
        border.append(rgb.getpixel((w - 1, y)))
    bg = Counter(border).most_common(1)[0][0]
    if min(bg) < SILHOUETTE_BG_MIN_CHANNEL:
        return rgb.convert("RGBA")

    def _near_bg(pos) -> bool:
        r, g, b = rgb.getpixel(pos)[:3]
        return (
            abs(r - bg[0]) <= SILHOUETTE_BG_TOLERANCE
            and abs(g - bg[1]) <= SILHOUETTE_BG_TOLERANCE
            and abs(b - bg[2]) <= SILHOUETTE_BG_TOLERANCE
        )

    seeds = [(x, 0) for x in range(w)] + [(x, h - 1) for x in range(w)]
    seeds += [(0, y) for y in range(h)] + [(w - 1, y) for y in range(h)]
    for seed in seeds:
        if rgb.getpixel(seed) == STRIP_MAGIC or not _near_bg(seed):
            continue
        ImageDraw.floodfill(rgb, seed, STRIP_MAGIC, thresh=SILHOUETTE_BG_TOLERANCE)

    rgba = rgb.convert("RGBA")
    data = []
    for r, g, b, a in rgba.getdata():
        if (r, g, b) == STRIP_MAGIC:
            data.append((r, g, b, 0))
        else:
            data.append((r, g, b, a))
    rgba.putdata(data)
    return rgba


def save_silhouette_upload(upload: UploadFile, prefix: str) -> str:
    """Силуэт для частиц: белая подложка убирается в прозрачность, размер до 512px."""
    ctype = (upload.content_type or "").lower()
    if not ctype.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Файл должен быть изображением")
    buf = _read_raw(upload, config.UPLOAD_MAX_BYTES, "Файл")

    from PIL import Image

    try:
        img = Image.open(io.BytesIO(buf))
        img.load()
    except (OSError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось прочитать изображение: файл повреждён или формат не поддерживается",
        )

    longest = max(img.size)
    if longest > SILHOUETTE_MAX_SIZE:
        scale = SILHOUETTE_MAX_SIZE / longest
        img = img.resize(
            (max(1, int(img.size[0] * scale)), max(1, int(img.size[1] * scale))),
            Image.LANCZOS,
        )

    if _has_alpha(img):
        out = img.convert("RGBA")
    else:
        out = _strip_edge_white(img)

    out_io = io.BytesIO()
    out.save(out_io, format="PNG", optimize=True)
    name = f"{prefix}_{int(time.time())}_{os.urandom(3).hex()}.png"
    path = os.path.join(config.UPLOADS_DIR, name)
    with open(path, "wb") as fh:
        fh.write(out_io.getvalue())
    return f"/api/uploads/{name}"


def save_audio_upload(upload: UploadFile, prefix: str) -> str:
    ctype = (upload.content_type or "").lower()
    if not ctype.startswith("audio/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Файл должен быть аудио")
    buf = _read_raw(upload, config.UPLOAD_AUDIO_MAX_BYTES, "Файл")
    return _save_raw(buf, upload, prefix, "mp3")


def remove_upload(url: str | None) -> None:
    if not url:
        return
    s3 = _get_s3()
    if s3:
        key = s3.s3_key_from_url(url)
        if key:
            s3.delete_object(key)
            return
    name = url.rsplit("/", 1)[-1]
    path = os.path.join(config.UPLOADS_DIR, name)
    if os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass
