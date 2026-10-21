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

      {!loaded ? (
        <div className="fm-card" style={{ marginTop: 12, display: 'flex', justifyContent: 'center', padding: 16 }}>
          <span className="fm-spinner" />
        </div>
      ) : holidays.length === 0 ? (
        <div className="fm-card" style={{ marginTop: 12, color: 'var(--text-muted)', textAlign: 'center' }}>
          Праздников пока нет — создайте первый по кнопке «Новый праздник»
        </div>
      ) : (
        <div style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}>
          {holidays.map((h) => (
            <div key={h.id} className="fm-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <h3 style={{ margin: 0 }}>{h.title}</h3>
                <span className="fm-chip">{STATUS_LABELS[h.status]}</span>
              </div>
              <div style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 8 }}>
                🗓 {h.starts_at.slice(0, 10).split('-').reverse().join('.')} — {h.ends_at.slice(0, 10).split('-').reverse().join('.')}
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>
                категорий: {h.categories_count} · карточек: {h.cards_count}
              </div>
              <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
                <button className="fm-btn fm-btn-sm fm-btn-outline" onClick={() => navigate(`/admin/holidays/${h.id}`)}>
                  ✏️ Изменить
                </button>
                <button className="fm-btn fm-btn-sm fm-btn-danger" onClick={() => remove(h.id)}>
                  🗑
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
