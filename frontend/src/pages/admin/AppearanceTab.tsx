import { useCallback, useEffect, useState } from 'react';
import { api, type Appearance } from '../../api/endpoints';
import { mediaUrl } from '../../api/media';

function AppearanceImageRow({
  title,
  hint,
  url,
  kind,
  onChanged,
}: {
  title: string;
  hint: string;
  url: string | null;
  kind: 'game_bg' | 'collection_bg';
  onChanged: () => void;
}) {
  const [busy, setBusy] = useState(false);

  async function clear() {
    if (!window.confirm(`Убрать картинку «${title}»?`)) return;
    setBusy(true);
    try {
      await api.adminClearAppearance(kind);
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fm-card" style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
      {url ? (
        <img src={mediaUrl(url)} alt="" style={{ height: 64, borderRadius: 8, objectFit: 'cover', minWidth: 100 }} />
      ) : (
        <div
          style={{
            height: 64,
            width: 100,
            borderRadius: 8,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'var(--surface-strong)',
            fontSize: 26,
          }}
        >
          🖼
        </div>
      )}
      <div style={{ flex: 1, minWidth: 160 }}>
        <div style={{ fontSize: 15 }}>{title}</div>
        <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>{hint}</div>
      </div>
      <label className="fm-btn" style={{ cursor: 'pointer' }}>
        {busy ? <span className="fm-spinner" /> : 'Загрузить'}
        <input
          type="file"
          accept="image/*"
          style={{ display: 'none' }}
          onChange={async (e) => {
            const f = e.target.files?.[0];
            e.target.value = '';
            if (!f) return;
            setBusy(true);
            try {
              await api.adminUploadAppearance(kind, f);
              onChanged();
            } finally {
              setBusy(false);
            }
          }}
        />
      </label>
      {url && (
        <button className="fm-btn fm-btn-outline" onClick={clear} disabled={busy}>
          Убрать
        </button>
      )}
    </div>
  );
}

export default function AppearanceTab() {
  const [appearance, setAppearance] = useState<Appearance | null>(null);

  const load = useCallback(() => {
    api.appearance().then(setAppearance).catch(() => setAppearance(null));
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <>
      <div className="fm-card">
        <h2>🎨 Оформление</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
          Общие картинки приложения. Фон активного праздника (если задан) перекрывает фон игры.
        </p>
      </div>
      <div style={{ display: 'grid', gap: 10, marginTop: 12 }}>
        <AppearanceImageRow
          title="Фон игры"
          hint="Показывается на всех экранах, пока у активного праздника нет своего фона"
          url={appearance?.game_bg_url ?? null}
          kind="game_bg"
          onChanged={load}
        />
        <AppearanceImageRow
          title="Картинка для коллекции"
          hint="Баннер вверху страницы «Коллекция»"
          url={appearance?.collection_bg_url ?? null}
          kind="collection_bg"
          onChanged={load}
        />
      </div>
    </>
  );
}
