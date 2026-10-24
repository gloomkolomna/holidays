import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import client, { clearToken, saveToken } from '../api/client';
import { useVkBridge } from './VkBridgeContext';
import type { MeUser } from '../api/endpoints';

interface SessionState {
  user: MeUser | null;
  token: string | null;
  loading: boolean;
  error: string | null;
  errorCode: string | null;
  logout: () => void;
  refresh: () => Promise<void>;
}

const SessionContext = createContext<SessionState>({
  user: null,
  token: null,
  loading: true,
  error: null,
  errorCode: null,
  logout: () => {},
  refresh: async () => {},
});

const TOKEN_KEY = 'token';

function extractError(e: any): { message: string | null; code: string | null } {
  const detail = e?.response?.data?.detail;
  if (detail && typeof detail === 'object') {
    return { message: detail.message || 'Ошибка авторизации', code: detail.code || null };
  }
  return { message: (typeof detail === 'string' && detail) || 'Ошибка авторизации', code: null };
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const { vkUserId, loading: vkLoading, launchParams } = useVkBridge();
  const [user, setUser] = useState<MeUser | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem(TOKEN_KEY));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);

  // 1. Логин: когда есть vkUserId и нет валидного токена — получить новый.
  useEffect(() => {
    if (vkLoading || vkUserId == null) return;

    let cancelled = false;

    async function login() {
      try {
        const res = await client.post('/auth/session', { params: { ...launchParams, vk_user_id: String(vkUserId) } });
        if (cancelled) return;
        const t = res.data.token as string;
        saveToken(t);
        setToken(t);
        setError(null);
        setErrorCode(null);
      } catch (e: any) {
        if (cancelled) return;
        const { message, code } = extractError(e);
        setError(message);
        setErrorCode(code);
        setLoading(false);
      }
    }

    // Если токен уже есть — попробуем /me; если протух — перевыпустим.
    async function verify() {
      try {
        const res = await client.get('/me');
        if (cancelled) return;
        setUser(res.data);
        setLoading(false);
      } catch {
        await login();
      }
    }

    if (token) {
      verify();
    } else {
      login();
    }

    return () => { cancelled = true; };
  }, [vkUserId, vkLoading, token]);

  // 2. После получения токена — загрузить /me.
  useEffect(() => {
    if (!token || user) return;
    let cancelled = false;
    client.get('/me')
      .then((res) => { if (!cancelled) { setUser(res.data); setLoading(false); } })
      .catch((e) => {
        if (cancelled) return;
        const { message, code } = extractError(e);
        setError(message || 'Не удалось загрузить профиль');
        setErrorCode(code);
        setLoading(false);
      });
    return () => { cancelled = true; };
  }, [token, user]);

  function logout() {
    clearToken();
    setToken(null);
    setUser(null);
  }

  async function refresh() {
    try {
      const res = await client.post('/auth/session', {
        params: { ...launchParams, vk_user_id: String(vkUserId) },
      });
      saveToken(res.data.token);
      setToken(res.data.token);
      setError(null);
      setErrorCode(null);
      const me = await client.get('/me');
      setUser(me.data);
      setLoading(false);
    } catch (e: any) {
      const { message, code } = extractError(e);
      setError(message);
      setErrorCode(code);
      setLoading(false);
    }
  }

  return (
    <SessionContext.Provider value={{ user, token, loading, error, errorCode, logout, refresh }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  return useContext(SessionContext);
}
