import { useCallback, useEffect, useState } from 'react';
import { api, type Rewards } from '../api/endpoints';
import { errorMessage } from '../api/errors';
import { mediaUrl } from '../api/media';
import { useSession } from '../context/SessionContext';

export default function RewardsPage() {
  const { refresh } = useSession();
  const [data, setData] = useState<Rewards | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [boughtCode, setBoughtCode] = useState<string | null>(null);
  const [copied, setCopied] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      setData(await api.rewards());
      setError(null);
    } catch {
      setData(null);
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function buy(itemId: number) {
    setBusy(true);
    setError(null);
    try {
      const res = await api.buyReward(itemId);
      setBoughtCode(res.code);
      await load();
      await refresh();
    } catch (e: any) {
      setError(errorMessage(e, 'Не удалось купить'));
    } finally {
      setBusy(false);
    }
  }

  async function copyCode(purchaseId: number, code: string) {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(purchaseId);
      setTimeout(() => setCopied(null), 1500);
    } catch {
      /* clipboard недоступен */
    }
  }

  if (!loaded) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 32 }}>
        <span className="fm-spinner" />
      </div>
    );
  }

  return (
    <div className="fm-rise">
      <div className="fm-card">
        <h2>🏆 Награды</h2>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
          <span className="fm-chip">💎 Кристаллы: {data?.crystals ?? 0}</span>
          <span className="fm-chip">🏆 Кубков: {data?.trophies.length ?? 0}</span>
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: 14, margin: '10px 0 0' }}>
          +1 кристалл и кубок за каждый полностью собранный раздел праздника.
        </p>
      </div>

      {error && (
        <div className="fm-card" style={{ marginTop: 12, color: 'var(--danger)' }}>{error}</div>
      )}

      {boughtCode && (
        <div className="fm-card fm-pop" style={{ marginTop: 12, textAlign: 'center', borderColor: 'var(--success)' }}>
          <div style={{ fontSize: 26 }}>🎁</div>
          Промокод: <strong>{boughtCode}</strong>
        </div>
      )}

      {(data?.trophies.length ?? 0) > 0 && (
        <div className="fm-card" style={{ marginTop: 12 }}>
          <h3>Кубки за собранные разделы</h3>
          {data!.trophies.map((t) => (
            <div key={`${t.holiday_id}-${t.category_id}`} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', gap: 8 }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {t.trophy_image_url ? (
                  <img src={mediaUrl(t.trophy_image_url)} alt="" style={{ height: 44, borderRadius: 6 }} />
                ) : (
                  '🏆'
                )}
                {t.title} · {t.category_title}
              </span>
              <span className="fm-chip">+{t.crystals} 💎</span>
            </div>
          ))}
        </div>
      )}

      <div className="fm-card" style={{ marginTop: 12 }}>
        <h3>Лавка наград</h3>
        {(data?.items.length ?? 0) === 0 ? (
          <p style={{ color: 'var(--text-muted)' }}>Товаров пока нет — загляните позже.</p>
        ) : (
          <div className="fm-grid" style={{ marginTop: 8 }}>
            {data!.items.map((item) => (
              <div key={item.id} className="fm-card" style={{ textAlign: 'center' }}>
                {item.image_url ? (
                  <img src={mediaUrl(item.image_url)} alt={item.title} style={{ width: '100%', borderRadius: 8, marginBottom: 6 }} />
                ) : (
                  <div style={{ fontSize: 36, marginBottom: 6 }}>🎁</div>
                )}
                <div style={{ fontSize: 16 }}>{item.title}</div>
                {item.description && (
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 2 }}>{item.description}</div>
                )}
                <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>
                  Осталось: {item.codes_available}
                </div>
                <button
                  className="fm-btn fm-btn-sm"
                  style={{ marginTop: 8 }}
                  disabled={busy || data!.crystals < item.price_crystals || item.codes_available === 0}
                  onClick={() => buy(item.id)}
                >
                  Купить · 💎 {item.price_crystals}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {(data?.purchases.length ?? 0) > 0 && (
        <div className="fm-card" style={{ marginTop: 12 }}>
          <h3>Мои промокоды</h3>
          {data!.purchases.map((p) => (
            <div key={p.id} style={{ display: 'flex', gap: 8, alignItems: 'center', padding: '6px 0', flexWrap: 'wrap' }}>
              <span style={{ flex: 1, minWidth: 120 }}>{p.item_title}</span>
              <code style={{ background: 'var(--surface-strong)', padding: '3px 8px', borderRadius: 6, fontSize: 14 }}>
                {p.code}
              </code>
              <button className="fm-btn fm-btn-xs fm-btn-outline" onClick={() => copyCode(p.id, p.code)}>
                {copied === p.id ? '✓' : 'Копировать'}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
