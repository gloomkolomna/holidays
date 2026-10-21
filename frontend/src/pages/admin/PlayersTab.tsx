import { useCallback, useEffect, useState } from 'react';
import { api, type PlayerEntry } from '../../api/endpoints';

export default function PlayersTab() {
  const [players, setPlayers] = useState<PlayerEntry[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setPlayers(await api.adminPlayers());
      setError(null);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Не удалось загрузить игроков');
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <>
      <div className="fm-card">
        <h2>👥 Игроки</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
          Все игроки и их собранные коллекции. Имена подтягиваются из VK.
        </p>
        {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}
      </div>

      {!loaded ? (
        <div className="fm-card" style={{ marginTop: 12, display: 'flex', justifyContent: 'center', padding: 16 }}>
          <span className="fm-spinner" />
        </div>
      ) : (
        players.map((p) => (
          <div key={p.vk_id} className="fm-card" style={{ marginTop: 12 }}>
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
              <strong style={{ fontSize: 16 }}>{p.display_name}</strong>
              <span className="fm-chip">id {p.vk_id}</span>
              {p.role === 'admin' && <span className="fm-chip">⚙️ админ</span>}
              <span className="fm-chip">💎 {p.crystals}</span>
              <span className="fm-chip" style={{ marginLeft: 'auto' }}>карточек: {p.cards_total}</span>
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 10 }}>
              {p.collections.map((c) => (
                <span key={c.holiday_id} className="fm-chip">
                  {c.full ? '🏆' : '🃏'} {c.title}: {c.collected}/{c.total}
                </span>
              ))}
            </div>
          </div>
        ))
      )}
    </>
  );
}
