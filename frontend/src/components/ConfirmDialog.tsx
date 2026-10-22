import { createPortal } from 'react-dom';

export default function ConfirmDialog({
  title,
  text,
  confirmLabel = 'OK',
  cancelLabel = 'Отмена',
  busy = false,
  danger = true,
  onConfirm,
  onCancel,
}: {
  title: string;
  text?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  busy?: boolean;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return createPortal(
    <div
      onClick={() => { if (!busy) onCancel(); }}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 100,
        background: 'rgba(0,0,0,0.6)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 20,
      }}
    >
      <div
        className="fm-card fm-pop"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: 360, width: '100%', textAlign: 'center' }}
      >
        <h3 style={{ marginTop: 0 }}>{title}</h3>
        {text && <p style={{ color: 'var(--text-secondary)', fontSize: 15, marginBottom: 0 }}>{text}</p>}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 14 }}>
          <button className="fm-btn fm-btn-outline" disabled={busy} onClick={onCancel}>
            {cancelLabel}
          </button>
          <button className={danger ? 'fm-btn fm-btn-danger' : 'fm-btn'} disabled={busy} onClick={onConfirm}>
            {busy ? <span className="fm-spinner" /> : confirmLabel}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
