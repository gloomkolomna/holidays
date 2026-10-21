import { useState } from 'react';
import { useSession } from '../context/SessionContext';

export default function ComingSoon() {
  const { refresh } = useSession();
  const [checking, setChecking] = useState(false);

  async function onCheck() {
    setChecking(true);
    await refresh();
    setChecking(false);
  }

  return (
    <div className="fm-shell">
      <div className="fm-card fm-rise" style={{ marginTop: 48, textAlign: 'center' }}>
        <div style={{ fontSize: 40 }}>🎈</div>
        <h2>Скоро!</h2>
        <p style={{ color: 'var(--text-secondary)' }}>
          Праздник ещё готовится. Совсем скоро здесь начнётся веселье — заглядывайте позже!
        </p>
        <button className="fm-btn fm-btn-outline" onClick={onCheck} disabled={checking}>
          {checking ? <span className="fm-spinner" /> : 'Проверить снова'}
        </button>
      </div>
    </div>
  );
}
