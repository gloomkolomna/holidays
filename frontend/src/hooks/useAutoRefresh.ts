import { useEffect, useRef, useState } from 'react';

export function useAutoRefresh(fn: () => void, intervalMs = 10000) {
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const fnRef = useRef(fn);
  fnRef.current = fn;

  useEffect(() => {
    const tick = () => {
      if (document.hidden) return;
      fnRef.current();
      setUpdatedAt(new Date());
    };
    const timer = setInterval(tick, intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs]);

  const refresh = () => {
    fnRef.current();
    setUpdatedAt(new Date());
  };

  const label = updatedAt ? `обновлено ${updatedAt.toLocaleTimeString('ru-RU')}` : '';
  return { refresh, label };
}
