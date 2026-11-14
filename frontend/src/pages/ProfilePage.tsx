import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'

export function ProfilePage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [repeatPassword, setRepeatPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    if (newPassword.length < 8) {
      setError('Новый пароль должен быть не короче 8 символов')
      return
    }
    if (newPassword !== repeatPassword) {
      setError('Новый пароль и повтор не совпадают')
      return
    }

    setBusy(true)
    try {
      await api.changePassword({ current_password: currentPassword, new_password: newPassword })
      // Сервер закрыл сессию: входим заново с новым паролем.
      await logout()
      navigate('/login', { replace: true })
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page page--narrow">
      <header className="page__header">
        <p className="eyebrow">профиль сотрудника</p>
        <h1>
          Смена <em>пароля</em>
        </h1>
        <p className="page__subtitle">
          {user?.full_name} · {user?.email}
        </p>
      </header>

      <div className="card">
        <form className="form" onSubmit={handleSubmit}>
          <label className="field">
            <span>Текущий пароль</span>
            <input
              type="password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </label>

          <label className="field">
            <span>Новый пароль</span>
            <input
              type="password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              autoComplete="new-password"
              minLength={8}
              required
            />
          </label>

          <label className="field">
            <span>Повторите новый пароль</span>
            <input
              type="password"
              value={repeatPassword}
              onChange={(event) => setRepeatPassword(event.target.value)}
              autoComplete="new-password"
              minLength={8}
              required
            />
          </label>

          {error && (
            <p className="alert" role="alert">
              {error}
            </p>
          )}

          <p className="hint">
            После смены пароля потребуется войти заново. Забытый пароль может сбросить технолог в
            разделе «Справочники → Пользователи».
          </p>

          <button type="submit" className="button" disabled={busy}>
            {busy ? 'Сохраняем…' : 'Сменить пароль'}
          </button>
        </form>
      </div>
    </div>
  )
}
