import { useCallback, useEffect, useState } from 'react';
import { api, type DailyStats } from '../../api/endpoints';

function yesterday(): string {
  const d = new Date(Date.now() - 24 * 3600 * 1000);
  return d.toISOString().slice(0, 10);
}

export default function StatsTab() {
  const [day, setDay] = useState(yesterday());
  const [stats, setStats] = useState<DailyStats | null>(null);
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(async (target: string) => {
    try {
      setStats(await api.adminStatsDaily(target));
    } catch {
      setStats(null);
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => { load(day); }, [day, load]);

  return (
    <>
      <div className="fm-card">
        <h2>📊 Статистика сбора</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
          Сколько игроков собрали каждую карточку за выбранные сутки (по МСК).
        </p>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <input className="fm-input" style={{ maxWidth: 180 }} type="date" value={day} onChange={(e) => setDay(e.target.value)} />
          <button className="fm-btn fm-btn-outline" onClick={() => load(day)}>↻ Обновить</button>
          <button className="fm-btn fm-btn-outline" onClick={() => setDay(yesterday())}>Вчера</button>
          <button className="fm-btn fm-btn-outline" onClick={() => setDay(new Date().toISOString().slice(0, 10))}>Сегодня</button>
        </div>
      </div>

      <div className="fm-card" style={{ marginTop: 12 }}>
        {!loaded ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 16 }}>
            <span className="fm-spinner" />
          </div>
        ) : !stats || stats.rows.length === 0 ? (
          <p style={{ color: 'var(--text-muted)' }}>За этот день карточек не собрано.</p>
        ) : (
          <>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 10 }}>
              <span className="fm-chip">Собрано карточек: {stats.total_cards}</span>
              <span className="fm-chip">Игроков собирало: {stats.total_players}</span>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table className="fm-table">
                <thead>
                  <tr>
                    <th>Праздник</th>
                    <th>Карточка</th>
                    <th>Игроков</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.rows.map((r) => (
                    <tr key={r.card_id}>
                      <td>{r.holiday_title}</td>
                      <td>
                        {r.is_trophy ? '🏆 ' : ''}{r.title}
                      </td>
                      <td>{r.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </>
  );
}
