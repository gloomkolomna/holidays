import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, type Holiday } from '../../api/endpoints';

const STATUS_LABELS: Record<string, string> = {
  upcoming: '⏳ будущий',
  active: '🟢 активный',
  finished: '🏁 завершён',
};

export default function HolidaysList() {
  const [holidays, setHolidays] = useState<Holiday[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const navigate = useNavigate();

  const load = useCallback(async () => {
    try {
      setHolidays(await api.adminHolidays());
      setError(null);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Не удалось загрузить праздники');
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function remove(id: number) {
    if (!window.confirm('Удалить праздник вместе с карточками?')) return;
    try {
      await api.adminDeleteHoliday(id);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Не удалось удалить');
    }
  }

  return (
    <>
      <div className="fm-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <h2 style={{ margin: 0 }}>🎃 Праздники</h2>
        <Link className="fm-btn" to="/admin/holidays/new">
          ➕ Новый праздник
        </Link>
      </div>

      {error && (
        <div className="fm-card" style={{ marginTop: 12, color: 'var(--danger)' }}>{error}</div>
      )}

      <div className="fm-card" style={{ marginTop: 12, overflowX: 'auto' }}>
        {!loaded ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 16 }}>
            <span className="fm-spinner" />
          </div>
        ) : (
          <table className="fm-table">
            <thead>
              <tr>
                <th>Название</th>
                <th>Сроки</th>
                <th>Категорий</th>
                <th>Карточек</th>
                <th>Статус</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {holidays.map((h) => (
                <tr key={h.id}>
                  <td>{h.title}</td>
                  <td style={{ whiteSpace: 'nowrap' }}>
                    {h.starts_at.slice(0, 10).split('-').reverse().join('.')} —{' '}
                    {h.ends_at.slice(0, 10).split('-').reverse().join('.')}
                  </td>
                  <td>{h.categories_count}</td>
                  <td>{h.cards_count}</td>
                  <td>{STATUS_LABELS[h.status]}</td>
                  <td style={{ whiteSpace: 'nowrap' }}>
                    <button className="fm-btn fm-btn-xs fm-btn-outline" onClick={() => navigate(`/admin/holidays/${h.id}`)}>
                      ✏️ Изменить
                    </button>{' '}
                    <button className="fm-btn fm-btn-xs fm-btn-danger" onClick={() => remove(h.id)}>
                      🗑
                    </button>
                  </td>
                </tr>
              ))}
              {holidays.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ color: 'var(--text-muted)' }}>
                    Праздников пока нет — создайте первый по кнопке «Новый праздник»
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
