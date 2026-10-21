import { useEffect, useState } from 'react';
import { api } from '../../api/endpoints';

export default function SettingsTab() {
  const [gameOpen, setGameOpen] = useState<boolean | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.adminGameState()
      .then((r) => setGameOpen(r.game_open))
      .catch(() => setError('Не удалось загрузить настройки'));
  }, []);

  async function toggle(value: boolean) {
    if (gameOpen === value || saving) return;
    setError(null);
    setSaving(true);
    try {
      const r = await api.adminSetGameState(value);
      setGameOpen(r.game_open);
    } catch {
      setError('Не удалось сохранить — попробуйте ещё раз');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fm-card fm-rise">
      <h3 style={{ marginBottom: 4 }}>🚪 Доступ к игре</h3>
      <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 0 }}>
        Пока игра закрыта, обычные игроки видят экран «Скоро» и не регистрируются.
        Администраторы входят всегда.
      </p>

      {error && <p style={{ color: 'var(--danger, #e5484d)', fontSize: 13 }}>{error}</p>}

      <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap', marginTop: 12 }}>
        <button
          className={`fm-btn${gameOpen === true ? '' : ' fm-btn-outline'}`}
          onClick={() => toggle(true)}
          disabled={gameOpen === null || saving}
        >
          {saving && gameOpen !== true ? <span className="fm-spinner" /> : '🎈 Игра открыта'}
        </button>
        <button
          className={`fm-btn${gameOpen === false ? '' : ' fm-btn-outline'}`}
          onClick={() => toggle(false)}
          disabled={gameOpen === null || saving}
        >
          {saving && gameOpen !== false ? <span className="fm-spinner" /> : '🔒 Игра закрыта'}
        </button>
      </div>

      <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 12 }}>
        {gameOpen === null
          ? 'Загрузка…'
          : gameOpen
            ? 'Сейчас: игра открыта — все подписчики группы могут входить и регистрироваться.'
            : 'Сейчас: игра закрыта — вход только для администраторов.'}
      </p>
    </div>
  );
}
