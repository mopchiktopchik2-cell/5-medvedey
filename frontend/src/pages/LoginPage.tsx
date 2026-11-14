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
      <div className="login__card">
        <div className="brand brand--login">
          <span className="brand__mark">М.и.Р.</span>
          <span className="brand__text">Швейный цех · Сургут</span>
        </div>

        <h1 className="login__title">Калькулятор себестоимости и раскроя</h1>
        <p className="login__subtitle">
          Вход для сотрудников цеха. Расчёт мерча и коммерческое предложение за 5–10 минут.
        </p>

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

          {error && <p className="alert" role="alert">{error}</p>}

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
