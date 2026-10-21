import { useEffect, useRef, useState } from 'react';
import { api } from '../api/endpoints';
import { useSession } from '../context/SessionContext';

export default function MusicPlayer({ src }: { src: string }) {
  const ref = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);
  const { refresh } = useSession();

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.play()
      .then(() => setPlaying(true))
      .catch(() => setPlaying(false));
    return () => {
      el.pause();
      setPlaying(false);
    };
  }, [src]);

  async function persist(enabled: boolean) {
    try {
      await api.setMusicEnabled(enabled);
      await refresh();
    } catch {
      /* ошибка сохранения — не мешаем локальному переключению */
    }
  }

  function toggle() {
    const el = ref.current;
    if (!el) return;
    if (el.paused) {
      el.play().then(() => setPlaying(true)).catch(() => setPlaying(false));
      void persist(true);
    } else {
      el.pause();
      setPlaying(false);
      void persist(false);
    }
  }

  return (
    <>
      <audio ref={ref} src={src} loop preload="auto" />
      <button
        className="fm-btn fm-btn-sm"
        style={{ position: 'fixed', right: 14, bottom: 14, zIndex: 40, borderRadius: 999, minWidth: 44 }}
        onClick={toggle}
        aria-label={playing ? 'Выключить музыку' : 'Включить музыку'}
        title={playing ? 'Пауза (музыка выключится и запомнится)' : 'Играть'}
      >
        {playing ? '🎵⏸' : '🎵'}
      </button>
    </>
  );
}
