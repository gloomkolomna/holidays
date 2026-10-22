import { useCallback, useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { Link, useParams } from 'react-router-dom';
import { api, type PlayerCardEntry, type PlayerDetail as PlayerDetailData, type PlayerReportEntry, type PlayerTaskEntry } from '../../api/endpoints';
import { mediaUrl } from '../../api/media';
import { useAutoRefresh } from '../../hooks/useAutoRefresh';

function fmtDateTime(iso: string | null): string {
  return iso ? new Date(iso + 'Z').toLocaleString('ru-RU') : '';
}

function dayLabel(day: string | null): string {
  return day ? day.split('-').reverse().join('.') : '';
}

function kindLabel(kind: string): string {
  return kind === 'penalty' ? 'Штрафное (магазин)' : 'Дневное';
}

function TaskCard({ task, onZoom }: { task: PlayerTaskEntry; onZoom: (url: string) => void }) {
  return (
    <div className="fm-card" style={{ marginTop: 12 }}>
      <h3>📌 Активное задание</h3>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
        <span className="fm-chip">{kindLabel(task.kind)}</span>
        <span className="fm-chip">{task.holiday_title}</span>
        <span className="fm-chip">норма: {task.required_crosses}</span>
        {task.taken_at && <span className="fm-chip">взято: {fmtDateTime(task.taken_at)}</span>}
      </div>
      <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', marginTop: 10, flexWrap: 'wrap' }}>
        {task.card_image_url && (
          <img
            src={mediaUrl(task.card_image_url)}
            alt={task.card_title}
            style={{ height: 110, borderRadius: 8, cursor: 'zoom-in', objectFit: 'cover' }}
            onClick={() => onZoom(task.card_image_url!)}
          />
        )}
        <div style={{ flex: 1, minWidth: 180 }}>
          <div style={{ fontSize: 16 }}>{task.card_title}</div>
          {task.card_day && (
            <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>🗓 {dayLabel(task.card_day)}</div>
          )}
          {task.card_task_text && (
            <div style={{ color: 'var(--text-secondary)', marginTop: 6 }}>{task.card_task_text}</div>
          )}
        </div>
      </div>
    </div>
  );
}

function ReportPhoto({ url, label, onZoom }: { url: string | null; label: string; onZoom: (u: string) => void }) {
  return (
    <div style={{ textAlign: 'center' }}>
      {url ? (
        <img
          src={mediaUrl(url)}
          alt={label}
          style={{ width: 96, height: 96, borderRadius: 8, cursor: 'zoom-in', objectFit: 'cover', display: 'block' }}
          onClick={() => onZoom(url)}
        />
      ) : (
        <div
          style={{
            width: 96,
            height: 96,
            borderRadius: 8,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'var(--surface-strong)',
            border: '1px dashed var(--border)',
          }}
        >
          📷
        </div>
      )}
      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>{label}</div>
    </div>
  );
}

export default function PlayerDetail() {
  const { vkId } = useParams();
  const [data, setData] = useState<PlayerDetailData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [zoomImg, setZoomImg] = useState<string | null>(null);

  const load = useCallback(() => {
    api.adminPlayer(Number(vkId))
      .then((d) => {
        setData(d);
        setError(null);
      })
      .catch((e: any) => setError(e?.response?.data?.detail || 'Не удалось загрузить игрока'));
  }, [vkId]);

  useEffect(() => {
    setData(null);
    setError(null);
    load();
  }, [load]);

  const { refresh, label } = useAutoRefresh(load);

  if (error && !data) {
    return (
      <div className="fm-rise">
        <div className="fm-card">
          <Link className="fm-btn fm-btn-outline fm-btn-sm" to="/admin/players">← Игроки</Link>
          <p style={{ color: 'var(--danger)', marginTop: 10 }}>{error}</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="fm-rise" style={{ display: 'flex', justifyContent: 'center', padding: 32 }}>
        <span className="fm-spinner" />
      </div>
    );
  }

  const { player, active_task: task, cards, reports } = data;
  const byHoliday = new Map<number, { title: string; items: PlayerCardEntry[] }>();
  for (const c of cards) {
    const group = byHoliday.get(c.holiday_id) || { title: c.holiday_title, items: [] };
    group.items.push(c);
    byHoliday.set(c.holiday_id, group);
  }

  return (
    <div className="fm-rise">
      {zoomImg && createPortal(
        <div
          onClick={() => setZoomImg(null)}
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 100,
            background: 'rgba(0,0,0,0.88)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'zoom-out',
          }}
        >
          <img src={mediaUrl(zoomImg)} alt="" style={{ maxWidth: '90vw', maxHeight: '85vh', borderRadius: 10 }} />
        </div>,
        document.body,
      )}

      <div className="fm-card">
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <Link className="fm-btn fm-btn-outline fm-btn-sm" to="/admin/players">← Игроки</Link>
          <button className="fm-btn fm-btn-outline fm-btn-sm" onClick={refresh}>↻ Обновить</button>
          {label && <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{label}</span>}
        </div>
        <h2 style={{ marginTop: 10 }}>{player.display_name}</h2>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
          <span className="fm-chip">id {player.vk_id}</span>
          {player.role === 'admin' && <span className="fm-chip">⚙️ админ</span>}
          <span className="fm-chip">💎 {player.crystals}</span>
          <span className="fm-chip">карточек: {player.cards_total}</span>
        </div>
        {error && (
          <p style={{ color: 'var(--danger)', marginTop: 8, marginBottom: 0, fontSize: 13 }}>{error}</p>
        )}
      </div>

      {task ? (
        <TaskCard task={task} onZoom={setZoomImg} />
      ) : (
        <div className="fm-card" style={{ marginTop: 12 }}>
          <h3>📌 Активное задание</h3>
          <p style={{ color: 'var(--text-muted)', marginTop: 6 }}>Нет активного задания</p>
        </div>
      )}

      <div className="fm-card" style={{ marginTop: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <h3 style={{ margin: 0 }}>📋 Отчёты</h3>
          <span className="fm-chip">всего: {reports.length}</span>
        </div>
        {reports.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', marginTop: 6 }}>Отчётов пока нет</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 12 }}>
            {reports.map((r: PlayerReportEntry) => (
              <div key={r.id} className="fm-card" style={{ padding: 10 }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{fmtDateTime(r.created_at)}</span>
                  <span style={{ fontSize: 14 }}>{r.card_title || '—'}</span>
                  {r.holiday_title && <span className="fm-chip">{r.holiday_title}</span>}
                  <span className="fm-chip" style={{ marginLeft: 'auto' }}>✖️ {r.amount}</span>
                </div>
                <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
                  <ReportPhoto url={r.photo_before} label="до" onZoom={setZoomImg} />
                  <ReportPhoto url={r.photo_after} label="после" onZoom={setZoomImg} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="fm-card" style={{ marginTop: 12 }}>
        <h3>🃏 Коллекция</h3>
        {cards.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', marginTop: 6 }}>Пока нет собранных карточек</p>
        ) : (
          [...byHoliday.entries()].map(([holidayId, group]) => (
            <div key={holidayId} style={{ marginTop: 14 }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                <strong>{group.title}</strong>
                <span className="fm-chip">карточек: {group.items.length}</span>
              </div>
              <div className="fm-grid" style={{ marginTop: 10 }}>
                {group.items.map((c) => (
                  <div key={c.card_id} className="fm-card" style={{ textAlign: 'center' }}>
                    {c.image_url ? (
                      <img
                        src={mediaUrl(c.image_url)}
                        alt={c.title}
                        style={{ width: '100%', borderRadius: 8, cursor: 'zoom-in' }}
                        onClick={() => setZoomImg(c.image_url)}
                      />
                    ) : (
                      <div style={{ fontSize: 28 }}>🃏</div>
                    )}
                    <div style={{ fontSize: 14, marginTop: 6 }}>{c.title}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                      {c.category_title}
                      {c.day ? ` · ${dayLabel(c.day)}` : ''}
                      {c.source === 'penalty' ? ' · выкуп' : ''}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
