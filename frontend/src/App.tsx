import { useEffect, useState, type FormEvent } from 'react'
import { api, type Note } from './api'

type Status = 'loading' | 'ready' | 'error'

function App() {
  const [notes, setNotes] = useState<Note[]>([])
  const [status, setStatus] = useState<Status>('loading')
  const [error, setError] = useState<string | null>(null)
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api
      .listNotes()
      .then((data) => {
        setNotes(data)
        setStatus('ready')
      })
      .catch((err: Error) => {
        setError(err.message)
        setStatus('error')
      })
  }, [])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!title.trim() || saving) return

    setSaving(true)
    setError(null)
    try {
      const created = await api.createNote({ title: title.trim(), body: body.trim() })
      setNotes((current) => [created, ...current])
      setTitle('')
      setBody('')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: number) {
    setError(null)
    try {
      await api.deleteNote(id)
      setNotes((current) => current.filter((note) => note.id !== id))
    } catch (err) {
      setError((err as Error).message)
    }
  }

  return (
    <main className="page">
      <header className="page__header">
        <h1>5 медведей</h1>
        <p className="page__subtitle">Каркас интерфейса: список заметок из API</p>
      </header>

      <form className="card form" onSubmit={handleSubmit}>
        <label className="field">
          <span>Заголовок</span>
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Что нужно сделать"
            maxLength={200}
            required
          />
        </label>

        <label className="field">
          <span>Описание</span>
          <textarea
            value={body}
            onChange={(event) => setBody(event.target.value)}
            placeholder="Необязательно"
            rows={3}
          />
        </label>

        <button type="submit" className="button" disabled={saving || !title.trim()}>
          {saving ? 'Сохраняем…' : 'Добавить'}
        </button>
      </form>

      {error && <p className="alert" role="alert">{error}</p>}

      {status === 'loading' && <p className="hint">Загружаем данные…</p>}

      {status === 'ready' && notes.length === 0 && (
        <p className="hint">Пока пусто — добавь первую запись.</p>
      )}

      <ul className="list">
        {notes.map((note) => (
          <li key={note.id} className="card list__item">
            <div>
              <h2 className="list__title">{note.title}</h2>
              {note.body && <p className="list__body">{note.body}</p>}
              <time className="list__date" dateTime={note.created_at}>
                {new Date(note.created_at).toLocaleString('ru-RU')}
              </time>
            </div>
            <button
              type="button"
              className="button button--ghost"
              onClick={() => handleDelete(note.id)}
              aria-label={`Удалить «${note.title}»`}
            >
              Удалить
            </button>
          </li>
        ))}
      </ul>
    </main>
  )
}

export default App
