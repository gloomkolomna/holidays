import { useState } from 'react';
import { api } from '../api/endpoints';
import { useSession } from '../context/SessionContext';

export default function Profile() {
  const { user, refresh } = useSession();
  const [music, setMusic] = useState(user ? user.music_enabled !== false : true);

  if (!user) return null;

  async function toggleMusic(value: boolean) {
    setMusic(value);
    try {
      await api.setMusicEnabled(value);
      await refresh();
    } catch {
      setMusic(!value);
    }
  }

  return (
    <div className="fm-rise">
      <div className="fm-card">
        <h2>{user.display_name || `Игрок ${user.vk_id}`}</h2>
        <div className="fm-stats" style={{ marginTop: 10 }}>
          <div className="fm-card" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 22 }}>💎</div>
            <div>{user.crystals}</div>
            <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>кристаллы</div>
          </div>
          <div className="fm-card" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 22 }}>🎭</div>
            <div>{user.role === 'admin' ? 'админ' : 'игрок'}</div>
            <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>роль</div>
          </div>
        </div>
        <label
          className="fm-card"
          style={{ marginTop: 12, display: 'flex', gap: 10, alignItems: 'center', cursor: 'pointer' }}
        >
          <input
            type="checkbox"
            checked={music}
            onChange={(e) => toggleMusic(e.target.checked)}
          />
          <span>🎵 Музыка праздника {music ? 'включена' : 'выключена'}</span>
        </label>
      </div>
    </div>
  );
}
