import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, type Shop, type ShopCard, type ShopHoliday } from '../api/endpoints';
import { mediaUrl } from '../api/media';

function dayLabel(day: string): string {
  return day.split('-').reverse().join('.');
}

export default function ShopPage() {
  const [shop, setShop] = useState<Shop | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [justTaken, setJustTaken] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setShop(await api.shop());
      setError(null);
    } catch {
      setShop(null);
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function take(card: ShopCard) {
    setBusy(true);
    setError(null);
    try {
      await api.shopTake(card.id);
      setJustTaken(card.title);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Не удалось взять карточку');
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
        <h2>🛒 Магазин выкупа</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: 15 }}>
          Пропустили карточку во время праздника? Здесь можно добрать любую несобранную —
          задание придёт со штрафом <strong>{shop?.penalty_crosses ?? 1000} крестиков</strong>.
          Одно выкупленное задание за раз, отказаться нельзя.
        </p>
        {shop?.has_active_task && (
          <div className="fm-card" style={{ marginTop: 8, textAlign: 'center' }}>
            У вас уже есть активное задание — сдайте его на главной, прежде чем выкупать новое.{' '}
            <Link to="/" style={{ color: 'var(--accent-warm)' }}>К заданию →</Link>
          </div>
        )}
      </div>

      {error && (
        <div className="fm-card" style={{ marginTop: 12, color: 'var(--danger)' }}>{error}</div>
      )}

      {justTaken && (
        <div className="fm-card fm-pop" style={{ marginTop: 12, textAlign: 'center', borderColor: 'var(--success)' }}>
          <div style={{ fontSize: 28 }}>🃏</div>
          Карточка «{justTaken}» принята в задания — сдайте отчёт на главной!
        </div>
      )}

      {shop && !shop.open ? (
        <div className="fm-card" style={{ marginTop: 12, textAlign: 'center' }}>
          <div style={{ fontSize: 28 }}>🔒</div>
          Магазин выкупа открыт по выходным — суббота и воскресенье
          (время московское). Загляните в ближайшую субботу!
        </div>
      ) : (shop?.holidays.length ?? 0) === 0 ? (
        <div className="fm-card" style={{ marginTop: 12, textAlign: 'center' }}>
          <div style={{ fontSize: 28 }}>🕳</div>
          Завершённых праздников с карточками для выкупа пока нет.
        </div>
      ) : (
        shop!.holidays.map((holiday: ShopHoliday) => (
          <div key={holiday.holiday_id} className="fm-card" style={{ marginTop: 12 }}>
            <h3>{holiday.title}</h3>
            <div className="fm-grid" style={{ marginTop: 12 }}>
              {holiday.cards.map((card) => (
                <div key={card.id} className="fm-card" style={{ textAlign: 'center' }}>
                  {card.image_url ? (
                    <img
                      src={mediaUrl(card.image_url)}
                      alt={card.title}
                      style={{ width: '100%', borderRadius: 8, marginBottom: 6 }}
                    />
                  ) : (
                    <div
                      style={{
                        width: '100%',
                        aspectRatio: '1',
                        borderRadius: 8,
                        marginBottom: 6,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        background: 'var(--surface-strong)',
                        fontSize: 30,
                      }}
                    >
                      🎴
                    </div>
                  )}
                  <div style={{ fontSize: 16 }}>{card.is_trophy ? '🏆 ' : ''}{card.title}</div>
                  <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>
                    {card.day ? `День ${dayLabel(card.day)} · ` : 'без даты · '}норма была {card.norm_crosses}
                  </div>
                  <button
                    className="fm-btn fm-btn-sm"
                    style={{ marginTop: 8 }}
                    disabled={busy || !!shop?.has_active_task}
                    onClick={() => take(card)}
                  >
                    Выкупить · {card.penalty_crosses} крестиков
                  </button>
                </div>
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
