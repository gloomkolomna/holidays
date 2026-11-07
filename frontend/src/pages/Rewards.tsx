import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, type Purchase, type Rewards } from '../api/endpoints';
import { errorMessage } from '../api/errors';
import { mediaUrl } from '../api/media';
import { useSession } from '../context/SessionContext';

const STATUS_LABELS = {
  available: 'Доступна',
  active: 'Действует',
  used: 'Использована',
  revoked: 'Обнулена',
};

export default function RewardsPage() {
  const { refresh } = useSession();
  const navigate = useNavigate();
  const [data, setData] = useState<Rewards | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

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
      await api.buyReward(itemId);
      setNotice('Награда добавлена в ваш инвентарь');
      await load();
      await refresh();
    } catch (e: any) {
      setError(errorMessage(e, 'Не удалось купить'));
    } finally {
      setBusy(false);
    }
  }

  async function apply(purchase: Purchase) {
    if (purchase.effect_type === 'complete_shop_card') {
      navigate(`/shop?reward_id=${purchase.id}`);
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await api.useReward(purchase.id);
      setNotice(purchase.effect_type.startsWith('external_') ? 'Награда выдана в другом приложении' : 'Награда применена');
      await load();
    } catch (e: any) {
      setError(errorMessage(e, 'Не удалось применить награду'));
      await load();
    } finally {
      setBusy(false);
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

      {error && <div className="fm-card" style={{ marginTop: 12, color: 'var(--danger)' }}>{error}</div>}
      {notice && <div className="fm-card fm-pop" style={{ marginTop: 12, borderColor: 'var(--success)' }}>{notice}</div>}

      {(data?.trophies.length ?? 0) > 0 && (
        <div className="fm-card" style={{ marginTop: 12 }}>
          <h3>Кубки за собранные разделы</h3>
          {data!.trophies.map((t) => (
            <div key={`${t.holiday_id}-${t.category_id}`} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', gap: 8 }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {t.trophy_image_url ? <img src={mediaUrl(t.trophy_image_url)} alt="" style={{ height: 44, borderRadius: 6 }} /> : '🏆'}
                {t.title} · {t.category_title}
              </span>
              <span className="fm-chip">+{t.crystals} 💎</span>
            </div>
          ))}
        </div>
      )}

      <div className="fm-card" style={{ marginTop: 12 }}>
        <h3>Лавка наград</h3>
        <div className="fm-grid" style={{ marginTop: 8 }}>
          {data?.items.map((item) => (
            <div key={item.id} className="fm-card" style={{ textAlign: 'center' }}>
              {item.image_url ? (
                <img src={mediaUrl(item.image_url)} alt={item.title} style={{ width: '100%', borderRadius: 8, marginBottom: 6 }} />
              ) : (
                <div style={{ fontSize: 36, marginBottom: 6 }}>🎁</div>
              )}
              <div style={{ fontSize: 16 }}>{item.title}</div>
              {item.description && <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 2 }}>{item.description}</div>}
              {item.effect_type === 'external_zakaz_discount' && (
                <div className="fm-chip" style={{ marginTop: 6 }}>Скидка {item.effect_config.percent}%</div>
              )}
              <button
                className="fm-btn fm-btn-sm"
                style={{ marginTop: 8 }}
                disabled={busy || data!.crystals < item.price_crystals}
                onClick={() => buy(item.id)}
              >
                Купить · 💎 {item.price_crystals}
              </button>
            </div>
          ))}
        </div>
      </div>

      {(data?.purchases.length ?? 0) > 0 && (
        <div className="fm-card" style={{ marginTop: 12 }}>
          <h3>Мои награды</h3>
          {data!.purchases.map((purchase) => (
            <div key={purchase.id} className="fm-card" style={{ marginTop: 8 }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                <strong style={{ flex: 1, minWidth: 180 }}>{purchase.item_title}</strong>
                <span className="fm-chip">{STATUS_LABELS[purchase.status]}</span>
                {purchase.effect_type === 'external_zakaz_discount' && (
                  <span className="fm-chip">{purchase.effect_config.percent}%</span>
                )}
              </div>
              {purchase.last_error && <p style={{ color: 'var(--danger)', fontSize: 13 }}>{purchase.last_error}</p>}
              {purchase.status === 'available' && purchase.effect_type && (
                <button className="fm-btn fm-btn-sm" style={{ marginTop: 8 }} disabled={busy} onClick={() => apply(purchase)}>
                  {purchase.effect_type === 'complete_shop_card' ? 'Выбрать карточку в магазине' : 'Применить'}
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
