import type { ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth'
import { Layout } from './components/Layout'
import { CalculatorPage } from './pages/CalculatorPage'
import { DictionariesPage } from './pages/DictionariesPage'
import { EstimatePage } from './pages/EstimatePage'
import { HistoryPage } from './pages/HistoryPage'
import { LoginPage } from './pages/LoginPage'
import { ProfilePage } from './pages/ProfilePage'
import { SharePage } from './pages/SharePage'

function RequireAuth() {
  const { user, loading } = useAuth()

  if (loading) {
    return <div className="boot">Загружаем систему…</div>
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <Layout />
}

function TechnologistOnly({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  if (user?.role !== 'technologist') {
    return <Navigate to="/" replace />
  }
  return <>{children}</>
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/share/:token" element={<SharePage />} />

          <Route element={<RequireAuth />}>
            <Route path="/" element={<CalculatorPage />} />
            <Route path="/estimates" element={<HistoryPage />} />
            <Route path="/estimates/:id" element={<EstimatePage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route
              path="/dictionaries"
              element={
                <TechnologistOnly>
                  <DictionariesPage />
                </TechnologistOnly>
              }
            />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
