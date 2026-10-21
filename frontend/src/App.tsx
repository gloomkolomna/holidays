import { Suspense, lazy, useEffect, useState } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { api, type Appearance, type HolidayDetail } from './api/endpoints';
import Background from './components/Background';
import MiniAppShell from './components/MiniAppShell';
import { useSession } from './context/SessionContext';
import { useVkBridge } from './context/VkBridgeContext';
import { applyPalette } from './theme';

const Home = lazy(() => import('./pages/Home'));
const Profile = lazy(() => import('./pages/Profile'));
const Admin = lazy(() => import('./pages/admin/Admin'));
const HolidaysList = lazy(() => import('./pages/admin/HolidaysList'));
const HolidayEdit = lazy(() => import('./pages/admin/HolidayEdit'));
const AppearanceTab = lazy(() => import('./pages/admin/AppearanceTab'));
const SettingsTab = lazy(() => import('./pages/admin/SettingsTab'));
const LogsTab = lazy(() => import('./pages/admin/LogsTab'));
const RewardsTab = lazy(() => import('./pages/admin/RewardsTab'));
const StatsTab = lazy(() => import('./pages/admin/StatsTab'));
const PlayersTab = lazy(() => import('./pages/admin/PlayersTab'));
const Rewards = lazy(() => import('./pages/Rewards'));
const Collection = lazy(() => import('./pages/Collection'));
const Shop = lazy(() => import('./pages/Shop'));
const MembersOnly = lazy(() => import('./pages/MembersOnly'));
const ComingSoon = lazy(() => import('./pages/ComingSoon'));

function Skeleton() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: '48px 0' }}>
      <span className="fm-spinner" />
    </div>
  );
}

function StubPage() {
  return (
    <div className="fm-shell">
      <div className="fm-card fm-rise" style={{ marginTop: 48, textAlign: 'center' }}>
        <h2>🎉 Улица праздников</h2>
        <p style={{ color: 'var(--text-secondary)' }}>
          Это мини-приложение ВК. Откройте его внутри ВКонтакте.
        </p>
      </div>
    </div>
  );
}

function ErrorScreen({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="fm-shell">
      <div className="fm-card fm-rise" style={{ marginTop: 48, textAlign: 'center' }}>
        <h2>Не удалось войти</h2>
        <p style={{ color: 'var(--text-secondary)' }}>{message}</p>
        <button className="fm-btn" onClick={onRetry}>
          Попробовать снова
        </button>
      </div>
    </div>
  );
}

export default function App() {
  const { vkUserId, loading: vkLoading } = useVkBridge();
  const { user, loading, error, errorCode, refresh } = useSession();
  const [activeHoliday, setActiveHoliday] = useState<HolidayDetail | null>(null);
  const [appearance, setAppearance] = useState<Appearance | null>(null);

  useEffect(() => {
    if (user) {
      api.activeHoliday().then(setActiveHoliday).catch(() => setActiveHoliday(null));
      api.appearance().then(setAppearance).catch(() => setAppearance(null));
    }
  }, [user]);

  useEffect(() => {
    applyPalette(activeHoliday?.palette);
  }, [activeHoliday?.palette]);

  if (vkLoading) return <Skeleton />;
  if (vkUserId == null) return <StubPage />;
  if (loading) return <Skeleton />;
  if (errorCode === 'game_closed') return <ComingSoon />;
  if (errorCode === 'members_only') return <MembersOnly />;
  if (!user) return <ErrorScreen message={error || 'Неизвестная ошибка'} onRetry={refresh} />;

  return (
    <>
      <Background url={activeHoliday?.bg_image_url || appearance?.game_bg_url} color={activeHoliday?.bg_color} />
      <MiniAppShell>
        <Suspense fallback={<Skeleton />}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/collection" element={<Collection />} />
            <Route path="/shop" element={<Shop />} />
            <Route path="/rewards" element={<Rewards />} />
            <Route path="/profile" element={<Profile />} />
            <Route
              path="/admin"
              element={user.role === 'admin' ? <Admin /> : <Navigate to="/" replace />}
            >
              <Route index element={<Navigate to="/admin/holidays" replace />} />
              <Route path="holidays" element={<HolidaysList />} />
              <Route path="holidays/new" element={<HolidayEdit />} />
              <Route path="holidays/:id" element={<HolidayEdit />} />
              <Route path="appearance" element={<AppearanceTab />} />
              <Route path="settings" element={<SettingsTab />} />
              <Route path="logs" element={<LogsTab />} />
              <Route path="rewards" element={<RewardsTab />} />
              <Route path="stats" element={<StatsTab />} />
              <Route path="players" element={<PlayersTab />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </MiniAppShell>
    </>
  );
}
