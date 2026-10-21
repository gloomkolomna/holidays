import { useCallback, useEffect, useState } from 'react';
import { api, type LogEntry } from '../../api/endpoints';

const LEVEL_LABELS: Record<string, string> = {
  '': 'все',
  info: 'info',
  warn: 'предупреждения',
  error: 'ошибки',
};

function fmtTime(iso: string): string {
  return iso ? new Date(iso + 'Z').toLocaleString('ru-RU') : '';
}

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

      {!loaded ? (
        <div className="fm-card" style={{ marginTop: 12, display: 'flex', justifyContent: 'center', padding: 16 }}>
          <span className="fm-spinner" />
        </div>
      ) : rows.length === 0 ? (
        <div className="fm-card" style={{ marginTop: 12, color: 'var(--text-muted)' }}>
          Записей нет — всё спокойно 🎉
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 12 }}>
          {rows.map((row) => {
            const lvlColor = row.level === 'error' ? 'var(--danger)' : 'var(--accent-warm)';
            return (
              <div key={row.id} className="fm-card" style={{ padding: 10, fontSize: 13 }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'monospace' }}>{fmtTime(row.created_at)}</span>
                  <span style={{ color: lvlColor, fontWeight: 600, fontSize: 11 }}>
                    {row.level === 'error' ? '🔴' : '🟡'} {row.level.toUpperCase()}
                  </span>
                  {row.status_code != null && (
                    <span style={{ fontSize: 11, fontFamily: 'monospace' }}>{row.status_code}</span>
                  )}
                  <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{row.method} {row.path}</span>
                  {row.event && <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>· {row.event}</span>}
                  {row.user_id != null && (
                    <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>· u{row.user_id}</span>
                  )}
                </div>
                {row.message && (
                  <pre style={{ marginTop: 6, marginBottom: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: 11, fontFamily: 'monospace', color: 'var(--text-secondary)', background: 'rgba(0,0,0,0.25)', padding: 8, borderRadius: 6 }}>
                    {row.message}
                  </pre>
                )}
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}
