import { useEffect, useState } from 'react';
import { api, type InfoBlock } from '../api/endpoints';

export default function Info() {
  const [blocks, setBlocks] = useState<InfoBlock[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    api.info()
      .then((d) => setBlocks(d.blocks))
      .catch(() => setFailed(true));
  }, []);

  if (failed) {
    return (
      <div className="fm-rise">
        <div className="fm-card">Не удалось загрузить информацию</div>
      </div>
    );
  }

  if (!blocks) {
    return (
      <div className="fm-rise" style={{ display: 'flex', justifyContent: 'center', padding: 32 }}>
        <span className="fm-spinner" />
      </div>
    );
  }

  return (
    <div className="fm-rise">
      {blocks.map((b, i) => (
        <div key={i} className="fm-card" style={i > 0 ? { marginTop: 12 } : undefined}>
          <h3>{b.title}</h3>
          <div style={{ color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', lineHeight: 1.7, marginTop: 6 }}>
            {b.text}
          </div>
        </div>
      ))}
    </div>
  );
}
