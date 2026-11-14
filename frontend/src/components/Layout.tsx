import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

const NAV = [
  { to: '/', end: true, index: '01', label: 'Калькулятор' },
  { to: '/estimates', end: false, index: '02', label: 'История' },
]

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
          <Link to="/" className="brand" aria-label="М.и.Р. — на главную">
            <span className="brand__mark">М</span>
            <span className="brand__text">
              <strong>М.и.Р.</strong>
              <small>швейный цех · сургут</small>
            </span>
          </Link>

          <nav className="nav" aria-label="Основная навигация">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  isActive ? 'nav__link nav__link--active' : 'nav__link'
                }
              >
                <span className="nav__index">{item.index}</span>
                {item.label}
              </NavLink>
            ))}
            {user?.role === 'technologist' && (
              <NavLink
                to="/dictionaries"
                className={({ isActive }) =>
                  isActive ? 'nav__link nav__link--active' : 'nav__link'
                }
              >
                <span className="nav__index">03</span>
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

        <div className="topbar__ticker" aria-hidden="true">
          <span>Швейный цех «М.и.Р.»</span>
          <span className="topbar__dot">●</span>
          <span>Себестоимость</span>
          <span className="topbar__dot">●</span>
          <span>Раскрой</span>
          <span className="topbar__dot">●</span>
          <span>Коммерческое предложение</span>
          <span className="topbar__ticker-end">Сургут · швейное производство</span>
        </div>
      </header>

      <main className="content">
        <Outlet />
      </main>
    </div>
  )
}
