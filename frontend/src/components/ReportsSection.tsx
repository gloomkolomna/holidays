import { useState } from 'react';
import { createPortal } from 'react-dom';
import type { PlayerReportEntry } from '../api/endpoints';
import { mediaUrl } from '../api/media';

function fmtDateTime(iso: string | null): string {
  return iso ? new Date(iso + 'Z').toLocaleString('ru-RU') : '';
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

export default function ReportsSection({ reports, title = '📋 Отчёты' }: { reports: PlayerReportEntry[]; title?: string }) {
  const [zoomImg, setZoomImg] = useState<string | null>(null);

  return (
    <>
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

      <div className="fm-card" style={{ marginTop: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <h3 style={{ margin: 0 }}>{title}</h3>
          <span className="fm-chip">всего: {reports.length}</span>
        </div>
        {reports.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', marginTop: 6 }}>Отчётов пока нет</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 12 }}>
            {reports.map((r) => (
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
    </>
  );
}
