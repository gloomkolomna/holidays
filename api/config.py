from __future__ import annotations
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

API_DIR = os.path.dirname(os.path.abspath(__file__))


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "")
    try:
        return int(str(raw).strip())
    except (ValueError, TypeError):
        return default


def _env_list_int(name: str) -> set[int]:
    raw = os.getenv(name, "")
    if not raw:
        return set()
    return {int(x.strip()) for x in raw.split(",") if x.strip().isdigit()}


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if raw == "":
        return default
    return raw in ("1", "true", "yes")


# ── Общие ──
SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = _env_int("ACCESS_TOKEN_EXPIRE_MINUTES", 259200)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///holiday.db")
APP_ENV = os.getenv("APP_ENV", "production").strip().lower()
DEV_LOGIN_ENABLED = APP_ENV == "dev"
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5176")

# ── VK Mini App ──
VK_APP_ID = _env_int("VK_APP_ID", 0)
VK_APP_SECRET = os.getenv("VK_APP_SECRET", "")
VK_SERVICE_TOKEN = os.getenv("VK_SERVICE_TOKEN", "")
VK_GROUP_ID = _env_int("VK_GROUP_ID", 0)
ADMIN_VK_IDS = _env_list_int("ADMIN_VK_IDS")

# ── Гейт подписки на группу ──
# Игра бесплатная и доступна только подписчикам группы ВК.
# В dev (.env) отключается, чтобы можно было работать без группы.
MEMBER_GATE_ENABLED = _env_bool("MEMBER_GATE_ENABLED", True)

# ── Бот итогов дня (wall.post от имени группы) ──
VK_GROUP_API_TOKEN = os.getenv("VK_GROUP_API_TOKEN", "")

# ── Логи ──
LOG_RETENTION_DAYS = _env_int("LOG_RETENTION_DAYS", 30)

# ── Загрузки (фото отчётов) ──
UPLOADS_DIR = os.getenv("UPLOADS_DIR", os.path.join(API_DIR, "uploads"))
os.makedirs(UPLOADS_DIR, exist_ok=True)
UPLOAD_MAX_BYTES = _env_int("UPLOAD_MAX_BYTES", 20 * 1024 * 1024)
UPLOAD_AUDIO_MAX_BYTES = _env_int("UPLOAD_AUDIO_MAX_BYTES", 20 * 1024 * 1024)

# ── S3 / Яндекс Object Storage (фото отчётов) ──
S3_ENABLED = os.getenv("S3_ENABLED", "").strip().lower() in ("1", "true", "yes")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "https://storage.yandexcloud.net")
S3_ACCESS_KEY_ID = os.getenv("S3_ACCESS_KEY_ID", "")
S3_SECRET_ACCESS_KEY = os.getenv("S3_SECRET_ACCESS_KEY", "")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "korgiholidays")
S3_PUBLIC_URL = os.getenv("S3_PUBLIC_URL", "").rstrip("/")


def get_admin_vk_ids() -> set[int]:
    return ADMIN_VK_IDS
