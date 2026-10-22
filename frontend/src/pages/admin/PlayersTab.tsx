import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, type PlayerEntry } from '../../api/endpoints';

export default function PlayersTab() {
  const [players, setPlayers] = useState<PlayerEntry[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const navigate = useNavigate();

  const load = useCallback(async (q: string) => {
    try {
      setPlayers(await api.adminPlayers(q || undefined));
      setError(null);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Не удалось загрузить игроков');
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    const t = setTimeout(() => load(search.trim()), 300);
    return () => clearTimeout(t);
  }, [load, search]);

  return (
    <>
      <div className="fm-card">
        <h2>👥 Игроки</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
          Все игроки и их собранные коллекции. Имена подтягиваются из VK.
        </p>
        <input
          className="fm-input"
          style={{ width: '100%', marginTop: 10 }}
          placeholder="Поиск: имя, фамилия или id"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}
      </div>

      {!loaded ? (
        <div className="fm-card" style={{ marginTop: 12, display: 'flex', justifyContent: 'center', padding: 16 }}>
          <span className="fm-spinner" />
        </div>
      ) : players.length === 0 ? (
        <div className="fm-card" style={{ marginTop: 12 }}>Ничего не найдено</div>
      ) : (
        players.map((p) => (
          <div
            key={p.vk_id}
            className="fm-card"
            style={{ marginTop: 12, cursor: 'pointer' }}
            onClick={() => navigate(`/admin/players/${p.vk_id}`)}
          >
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
            <div style={{ marginTop: 8, fontSize: 13, color: 'var(--text-muted)' }}>Задание и коллекция →</div>
          </div>
        ))
      )}
    </>
  );
}
