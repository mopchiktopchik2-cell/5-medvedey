import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

export function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar__inner">
          <div className="brand">
            <span className="brand__mark">М.и.Р.</span>
            <span className="brand__text">Калькулятор себестоимости</span>
          </div>

          <nav className="nav">
            <NavLink to="/" end className={({ isActive }) => (isActive ? 'nav__link nav__link--active' : 'nav__link')}>
              Калькулятор
            </NavLink>
            <NavLink
              to="/estimates"
              className={({ isActive }) => (isActive ? 'nav__link nav__link--active' : 'nav__link')}
            >
              История
            </NavLink>
            {user?.role === 'technologist' && (
              <NavLink
                to="/dictionaries"
                className={({ isActive }) =>
                  isActive ? 'nav__link nav__link--active' : 'nav__link'
                }
              >
                Справочники
              </NavLink>
            )}
          </nav>

          <div className="userbox">
            <div className="userbox__meta">
              <span className="userbox__name">{user?.full_name}</span>
              <span className="userbox__role">
                {user?.role === 'technologist' ? 'технолог' : 'менеджер'}
              </span>
            </div>
            <button type="button" className="button button--ghost button--small" onClick={handleLogout}>
              Выйти
            </button>
          </div>
        </div>
      </header>

      <main className="content">
        <Outlet />
      </main>
    </div>
  )
}
