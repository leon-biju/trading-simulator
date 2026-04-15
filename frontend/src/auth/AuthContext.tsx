import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import axios from 'axios'
import { injectAuthHandlers } from '@/lib/axios'

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
  getAccessToken: () => string | null
  setAccessToken: (token: string) => void
  loginWithToken: (token: string, user: User) => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

// Module-level singleton: ensures concurrent StrictMode double-mounts share
// one in-flight refresh request rather than racing to insert the same token.
let refreshPromise: Promise<{ access: string; user: User } | null> | null = null

function doSilentRefresh(): Promise<{ access: string; user: User } | null> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const { data: refreshData } = await axios.post(
          '/api/auth/token/refresh/',
          {},
          { withCredentials: true },
        )
        const { data: userData } = await axios.get('/api/users/me/', {
          headers: { Authorization: `Bearer ${refreshData.access}` },
        })
        return { access: refreshData.access, user: userData as User }
      } catch {
        return null
      } finally {
        refreshPromise = null
      }
    })()
  }
  return refreshPromise
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const accessTokenRef = useRef<string | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const getAccessToken = () => accessTokenRef.current
  const setAccessToken = (token: string) => {
    accessTokenRef.current = token
  }
  const clearAuth = () => {
    accessTokenRef.current = null
    setUser(null)
  }

  function loginWithToken(token: string, userData: User) {
    accessTokenRef.current = token
    setUser(userData)
  }

  // Inject handlers into the Axios interceptor so it can refresh tokens
  // and force logout without a circular import
  useEffect(() => {
    injectAuthHandlers(getAccessToken, clearAuth)
  })

  // On mount: attempt silent refresh using the httpOnly cookie
  useEffect(() => {
    let cancelled = false

    doSilentRefresh().then((result) => {
      if (cancelled) return
      if (result) {
        accessTokenRef.current = result.access
        setUser(result.user)
      }
      setIsLoading(false)
    })

    return () => {
      cancelled = true
    }
  }, [])

  async function login(credentials: { username: string; password: string }) {
    const { data } = await axios.post('/api/auth/token/', credentials, {
      withCredentials: true,
    })
    accessTokenRef.current = data.access

    const { data: userData } = await axios.get('/api/users/me/', {
      headers: { Authorization: `Bearer ${data.access}` },
    })
    setUser(userData)
  }

  async function logout() {
    try {
      await axios.post('/api/auth/token/blacklist/', {}, { withCredentials: true })
    } catch {
      // Ignore — clear locally regardless
    }
    clearAuth()
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: user !== null,
        login,
        logout,
        getAccessToken,
        setAccessToken,
        loginWithToken,
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
