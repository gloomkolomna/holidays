import { mediaUrl } from '../api/media';

export default function Background({ url, color }: { url?: string | null; color?: string | null }) {
  const bgUrl = url ? mediaUrl(url) : null;

  return (
    <div aria-hidden="true" style={{ position: 'fixed', inset: 0, zIndex: -3, overflow: 'hidden' }}>
      {bgUrl ? (
        <img
          src={bgUrl}
          alt=""
          draggable={false}
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            minWidth: '100%',
            minHeight: '100%',
            transform: 'translate(-50%, -50%)',
            objectFit: 'cover',
            width: '100%',
            height: '100%',
            userSelect: 'none',
            pointerEvents: 'none',
          }}
        />
      ) : (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: color
              ? `radial-gradient(ellipse at 50% 0%, ${color} 0%, ${color} 100%)`
              : 'radial-gradient(ellipse at 50% 0%, #4a2c6b 0%, #2b1a44 45%, #1a1030 100%)',
          }}
        />
      )}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          pointerEvents: 'none',
          background:
            'radial-gradient(ellipse at center, transparent 0%, rgba(18,10,32,0.35) 75%, rgba(10,6,20,0.55) 100%)',
        }}
      />
    </div>
  );
}
