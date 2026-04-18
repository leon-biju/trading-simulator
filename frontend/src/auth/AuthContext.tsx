import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import api from '@/lib/axios'

interface User {
  id: number
  username: string
  email: string
  home_currency: string
  display_name: string
  total_cash: string
}

interface AuthContextValue {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (credentials: { username: string; password: string }) => Promise<void>
  logout: () => Promise<void>
  loginDirect: (user: User) => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    api.get('/api/users/me/')
      .then(({ data }) => setUser(data as User))
      .catch(() => {})
      .finally(() => setIsLoading(false))
  }, [])

  async function login(credentials: { username: string; password: string }) {
    const { data } = await api.post('/api/auth/login/', credentials)
    setUser(data as User)
  }

  async function logout() {
    try { await api.post('/api/auth/logout/') } catch {}
    setUser(null)
  }

  function loginDirect(userData: User) {
    setUser(userData)
  }

  async function refreshUser() {
    const { data } = await api.get('/api/users/me/')
    setUser(data as User)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: user !== null,
        login,
        logout,
        loginDirect,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
