const API_URL = import.meta.env.VITE_API_URL ?? '/api'

export type Note = {
  id: number
  title: string
  body: string
  created_at: string
}

export type NoteInput = {
  title: string
  body?: string
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })

  if (!response.ok) {
    const detail = await response.json().catch(() => null)
    throw new Error(detail?.detail ?? `Запрос не удался: ${response.status}`)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

export const api = {
  listNotes: () => request<Note[]>('/notes'),
  createNote: (input: NoteInput) =>
    request<Note>('/notes', { method: 'POST', body: JSON.stringify(input) }),
  updateNote: (id: number, input: Partial<NoteInput>) =>
    request<Note>(`/notes/${id}`, { method: 'PATCH', body: JSON.stringify(input) }),
  deleteNote: (id: number) => request<void>(`/notes/${id}`, { method: 'DELETE' }),
  health: () => request<{ status: string; env: string }>('/health'),
}
