import { useCallback, useEffect, useState } from 'react'
import { api, type AdminUser, type Role } from '../api'

const ROLE_LABEL: Record<Role, string> = {
  manager: 'менеджер',
  technologist: 'технолог',
}

const BLANK = {
  email: '',
  full_name: '',
  role: 'manager' as Role,
  password: '',
}

export function UsersCard() {
  const [users, setUsers] = useState<AdminUser[]>([])
  const [draft, setDraft] = useState(BLANK)
  const [passwords, setPasswords] = useState<Record<number, string>>({})
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const reload = useCallback(async () => {
    try {
      setUsers(await api.listUsers())
    } catch (err) {
      setError((err as Error).message)
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  function patchUser(id: number, patch: Partial<AdminUser>) {
    setUsers((current) => current.map((user) => (user.id === id ? { ...user, ...patch } : user)))
  }

  async function handleCreate() {
    setBusy('new')
    setError(null)
    setNotice(null)
    try {
      await api.createUser({
        email: draft.email.trim(),
        full_name: draft.full_name.trim() || draft.email.trim(),
        role: draft.role,
        password: draft.password,
      })
      setDraft(BLANK)
      setNotice('Сотрудник добавлен')
      await reload()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(null)
    }
  }

  async function handleSave(user: AdminUser) {
    setBusy(String(user.id))
    setError(null)
    setNotice(null)
    const password = passwords[user.id]?.trim()
    try {
      await api.updateUser(user.id, {
        full_name: user.full_name,
        role: user.role,
        is_active: user.is_active,
        ...(password ? { password } : {}),
      })
      setPasswords((current) => ({ ...current, [user.id]: '' }))
      setNotice('Изменения сохранены')
      await reload()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="stack">
      <p className="hint">
        Технолог заводит сотрудников и может сбросить забытый пароль. Свой пароль каждый меняет в
        разделе «Сменить пароль». Отключённый сотрудник не может войти, но его расчёты остаются в
        истории.
      </p>

      {error && (
        <p className="alert" role="alert">
          {error}
        </p>
      )}
      {notice && <p className="notice notice--ok">{notice}</p>}

      <table className="table table--compact">
        <thead>
          <tr>
            <th>ФИО</th>
            <th>Email</th>
            <th>Роль</th>
            <th>Статус</th>
            <th>Новый пароль</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.id}>
              <td>
                <input
                  value={user.full_name}
                  onChange={(event) => patchUser(user.id, { full_name: event.target.value })}
                />
              </td>
              <td className="table__muted">{user.email}</td>
              <td>
                <select
                  value={user.role}
                  onChange={(event) => patchUser(user.id, { role: event.target.value as Role })}
                >
                  {(Object.keys(ROLE_LABEL) as Role[]).map((role) => (
                    <option key={role} value={role}>
                      {ROLE_LABEL[role]}
                    </option>
                  ))}
                </select>
              </td>
              <td>
                <select
                  value={user.is_active ? 'true' : 'false'}
                  onChange={(event) =>
                    patchUser(user.id, { is_active: event.target.value === 'true' })
                  }
                >
                  <option value="true">Работает</option>
                  <option value="false">Отключён</option>
                </select>
              </td>
              <td>
                <input
                  type="password"
                  placeholder="не менять"
                  autoComplete="new-password"
                  value={passwords[user.id] ?? ''}
                  onChange={(event) =>
                    setPasswords((current) => ({ ...current, [user.id]: event.target.value }))
                  }
                />
              </td>
              <td className="table__action">
                <button
                  type="button"
                  className="button button--ghost button--small"
                  onClick={() => void handleSave(user)}
                  disabled={busy === String(user.id)}
                >
                  {busy === String(user.id) ? '…' : 'Сохранить'}
                </button>
              </td>
            </tr>
          ))}

          <tr className="table__new">
            <td>
              <input
                placeholder="Иванов И. И."
                value={draft.full_name}
                onChange={(event) => setDraft({ ...draft, full_name: event.target.value })}
              />
            </td>
            <td>
              <input
                type="email"
                placeholder="ivanov@mir.ru"
                value={draft.email}
                onChange={(event) => setDraft({ ...draft, email: event.target.value })}
              />
            </td>
            <td>
              <select
                value={draft.role}
                onChange={(event) => setDraft({ ...draft, role: event.target.value as Role })}
              >
                {(Object.keys(ROLE_LABEL) as Role[]).map((role) => (
                  <option key={role} value={role}>
                    {ROLE_LABEL[role]}
                  </option>
                ))}
              </select>
            </td>
            <td className="table__muted">—</td>
            <td>
              <input
                type="password"
                placeholder="минимум 8 символов"
                autoComplete="new-password"
                value={draft.password}
                onChange={(event) => setDraft({ ...draft, password: event.target.value })}
              />
            </td>
            <td className="table__action">
              <button
                type="button"
                className="button button--ghost button--small"
                onClick={() => void handleCreate()}
                disabled={busy === 'new' || !draft.email.trim() || draft.password.length < 8}
              >
                {busy === 'new' ? '…' : 'Добавить'}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}
