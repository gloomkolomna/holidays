import { useCallback, useEffect, useState } from 'react';
import { api, type LogEntry } from '../../api/endpoints';

const LEVEL_LABELS: Record<string, string> = {
  '': 'все',
  info: 'info',
  warn: 'предупреждения',
  error: 'ошибки',
};

export default function LogsTab() {
  const [rows, setRows] = useState<LogEntry[]>([]);
  const [level, setLevel] = useState('');
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(async (lvl: string) => {
    try {
      setRows(await api.adminLogs(lvl || undefined));
    } catch {
      setRows([]);
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => { load(level); }, [level, load]);

  return (
    <>
      <div className="fm-card">
        <h2>📜 Логи</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: 15 }}>
          Последние 50 записей: неуспешные запросы (4xx/5xx) и ошибки сервера.
        </p>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <select className="fm-input" style={{ maxWidth: 220 }} value={level} onChange={(e) => setLevel(e.target.value)}>
            {Object.entries(LEVEL_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
          <button className="fm-btn fm-btn-outline" onClick={() => load(level)}>
            ↻ Обновить
          </button>
        </div>
      </div>

      <div className="fm-card" style={{ marginTop: 12, overflowX: 'auto' }}>
        {!loaded ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 16 }}>
            <span className="fm-spinner" />
          </div>
        ) : rows.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', margin: 0 }}>Записей нет — всё спокойно 🎉</p>
        ) : (
          <table className="fm-table">
            <thead>
              <tr>
                <th>Время</th>
                <th>Уровень</th>
                <th>Запрос</th>
                <th>Игрок</th>
                <th>Сообщение</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td style={{ whiteSpace: 'nowrap' }}>
                    {row.created_at ? new Date(row.created_at + 'Z').toLocaleString('ru-RU') : ''}
                  </td>
                  <td style={{ color: row.level === 'error' ? 'var(--danger)' : 'var(--accent-warm)' }}>
                    {row.level === 'error' ? '🔴' : '🟡'} {row.level}
                  </td>
                  <td style={{ whiteSpace: 'nowrap' }}>
                    {row.method} {row.path}
                    {row.status_code != null && <span style={{ color: 'var(--text-muted)' }}> → {row.status_code}</span>}
                  </td>
                  <td>{row.user_id ?? '—'}</td>
                  <td title={row.message ?? ''} style={{ maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {row.message ?? ''}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
