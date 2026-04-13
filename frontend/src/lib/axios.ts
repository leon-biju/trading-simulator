import axios from 'axios'

// Module-level token accessors — injected by AuthContext after mount
// to avoid circular imports between axios.ts and AuthContext.tsx
let _getToken: () => string | null = () => null
let _clearAuth: () => void = () => {}

export function injectAuthHandlers(
  getToken: () => string | null,
  clearAuth: () => void,
) {
  _getToken = getToken
  _clearAuth = clearAuth
}

const api = axios.create({
  baseURL: '',
  withCredentials: true, // send httpOnly refresh cookie on every request
})

// Attach Bearer token to every request
api.interceptors.request.use((config) => {
  const token = _getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 → silent refresh → retry once
let isRefreshing = false
let refreshSubscribers: Array<(token: string) => void> = []

function subscribeToRefresh(cb: (token: string) => void) {
  refreshSubscribers.push(cb)
}

function notifySubscribers(token: string) {
  refreshSubscribers.forEach((cb) => cb(token))
  refreshSubscribers = []
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config

    if (error.response?.status !== 401 || original._retry) {
      return Promise.reject(error)
    }

    original._retry = true

    if (isRefreshing) {
      // Queue until the in-flight refresh completes
      return new Promise((resolve) => {
        subscribeToRefresh((newToken) => {
          original.headers.Authorization = `Bearer ${newToken}`
          resolve(api(original))
        })
      })
    }

    isRefreshing = true

    try {
      const { data } = await axios.post(
        '/api/auth/token/refresh/',
        {},
        { withCredentials: true },
      )
      const newToken: string = data.access

      // Update the in-memory token via AuthContext
      injectAuthHandlers(() => newToken, _clearAuth)
      notifySubscribers(newToken)

      original.headers.Authorization = `Bearer ${newToken}`
      return api(original)
    } catch {
      // Refresh failed — force logout
      _clearAuth()
      window.location.href = '/login'
      return Promise.reject(error)
    } finally {
      isRefreshing = false
    }
  },
)

export default api
