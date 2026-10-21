import { useEffect, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { NavLink, useLocation } from 'react-router-dom';
import { useSession } from '../context/SessionContext';

interface Tab {
  to: string;
  label: string;
  end?: boolean;
}

const BASE_TABS: Tab[] = [
  { to: '/', label: '🎉 Главная', end: true },
  { to: '/collection', label: '🃏 Коллекция' },
  { to: '/shop', label: '🛒 Магазин' },
  { to: '/rewards', label: '🏆 Награды' },
  { to: '/profile', label: '👤 Профиль' },
];

export default function MiniAppShell({ children }: { children: ReactNode }) {
  const { user } = useSession();
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  const tabs: Tab[] =
    user?.role === 'admin'
      ? [...BASE_TABS, { to: '/admin', label: '⚙️ Управление' }]
      : BASE_TABS;

  const activeTab = tabs.find((t) =>
    t.end ? location.pathname === t.to : location.pathname.startsWith(t.to),
  );
  const title = activeTab ? activeTab.label.replace(/^\S+\s/, '') : 'Улица праздников';

  return (
    <div className="fm-shell">
      <header className="fm-shell-header">
        <button
          className="fm-menu-btn"
          onClick={() => setMenuOpen((v) => !v)}
          aria-label="Меню"
        >
          ☰
        </button>
        <div className="fm-shell-title">{title}</div>
        <span className="fm-chip" title="Кристаллы">
          💎 {user?.crystals ?? 0}
        </span>
      </header>

      {menuOpen && createPortal(
        <div className="fm-menu-overlay" onClick={() => setMenuOpen(false)}>
          <nav className="fm-menu" onClick={(e) => e.stopPropagation()}>
            {tabs.map((t) => (
              <NavLink
                key={t.to}
                to={t.to}
                end={t.end}
                className={({ isActive }) => `fm-menu-item${isActive ? ' active' : ''}`}
                onClick={() => setMenuOpen(false)}
              >
                {t.label}
              </NavLink>
            ))}
          </nav>
        </div>,
        document.body,
      )}

      {children}
    </div>
  );
}
