import { useState } from 'react';
import { useSession } from '../context/SessionContext';

const GROUP_URL = import.meta.env.VITE_VK_GROUP_URL || '';

export default function MembersOnly() {
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
        <h2>Только для своих</h2>
        <p style={{ color: 'var(--text-secondary)' }}>
          Игра бесплатная и открыта для подписчиков нашей группы ВКонтакте.
          Подпишитесь — и праздники начнутся!
        </p>
        <div style={{ display: 'flex', gap: 10, justifyContent: 'center', marginTop: 14, flexWrap: 'wrap' }}>
          {GROUP_URL && (
            <a className="fm-btn" href={GROUP_URL} target="_blank" rel="noreferrer">
              Перейти к группе
            </a>
          )}
          <button className="fm-btn fm-btn-outline" onClick={onCheck} disabled={checking}>
            {checking ? <span className="fm-spinner" /> : 'Проверить снова'}
          </button>
        </div>
      </div>
    </div>
  );
}
