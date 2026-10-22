import { NavLink, Outlet } from 'react-router-dom';

export default function Admin() {
  return (
    <div className="fm-rise">
      <div className="fm-menu-tabs">
        <NavLink to="/admin/holidays" className={({ isActive }) => `fm-menu-tab${isActive ? ' active' : ''}`}>
          🎃 Праздники
        </NavLink>
        <NavLink to="/admin/appearance" className={({ isActive }) => `fm-menu-tab${isActive ? ' active' : ''}`}>
          🎨 Оформление
        </NavLink>
        <NavLink to="/admin/settings" className={({ isActive }) => `fm-menu-tab${isActive ? ' active' : ''}`}>
          ⚙️ Настройки
        </NavLink>
        <NavLink to="/admin/info" className={({ isActive }) => `fm-menu-tab${isActive ? ' active' : ''}`}>
          ℹ️ Информация
        </NavLink>
        <NavLink to="/admin/logs" className={({ isActive }) => `fm-menu-tab${isActive ? ' active' : ''}`}>
          📜 Логи
        </NavLink>
        <NavLink to="/admin/rewards" className={({ isActive }) => `fm-menu-tab${isActive ? ' active' : ''}`}>
          🏆 Награды
        </NavLink>
        <NavLink to="/admin/stats" className={({ isActive }) => `fm-menu-tab${isActive ? ' active' : ''}`}>
          📊 Статистика
        </NavLink>
        <NavLink to="/admin/players" className={({ isActive }) => `fm-menu-tab${isActive ? ' active' : ''}`}>
          👥 Игроки
        </NavLink>
      </div>

      <Outlet />
    </div>
  );
}
