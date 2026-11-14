import { useState, type FormEvent } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../auth'

export function LoginPage() {
  const { user, login } = useAuth()
  const [email, setEmail] = useState('manager@mir.ru')
  const [password, setPassword] = useState('manager123')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (user) {
    return <Navigate to="/" replace />
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await login(email.trim(), password)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login">
      <aside className="login__panel">
        <div className="brand">
          <span className="brand__mark">М</span>
          <span className="brand__text">
            <strong>М.и.Р.</strong>
            <small>швейный цех · сургут</small>
          </span>
        </div>

        <p className="eyebrow">внутренний инструмент цеха</p>
        <h1 className="login__title">
          Себестоимость <em>без сюрпризов</em>
        </h1>
        <p className="login__subtitle">
          Считаем материал, раскрой, пошив и брендирование — и собираем коммерческое предложение
          за 5–10 минут.
        </p>

        <ul className="login__points">
          <li>
            <span>01</span>Материал, раскрой и пошив в одном расчёте
          </li>
          <li>
            <span>02</span>КП в PDF с логотипом и реквизитами цеха
          </li>
          <li>
            <span>03</span>История расчётов и ссылка для заказчика
          </li>
        </ul>

        <div className="login__foot">М.и.Р. · калькулятор себестоимости и раскроя</div>
      </aside>

      <div className="login__card">
        <p className="eyebrow">вход для сотрудников</p>
        <h2 className="login__form-title">Вход в систему</h2>

        <form className="form" onSubmit={handleSubmit}>
          <label className="field">
            <span>Email</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="username"
              required
            />
          </label>

          <label className="field">
            <span>Пароль</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </label>

          {error && (
            <p className="alert" role="alert">
              {error}
            </p>
          )}

          <button type="submit" className="button" disabled={busy}>
            {busy ? 'Входим…' : 'Войти'}
          </button>
        </form>

        <div className="login__hint">
          <strong>Демо-доступы</strong>
          <div className="login__accounts">
            <button
              type="button"
              className="chip"
              onClick={() => {
                setEmail('manager@mir.ru')
                setPassword('manager123')
              }}
            >
              Менеджер · manager@mir.ru
            </button>
            <button
              type="button"
              className="chip"
              onClick={() => {
                setEmail('technologist@mir.ru')
                setPassword('technolog123')
              }}
            >
              Технолог · technologist@mir.ru
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
