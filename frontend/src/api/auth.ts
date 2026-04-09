import api from '@/lib/axios'

export interface RegisterPayload {
  username: string
  email: string
  password: string
  password2: string
  home_currency: string
}

export async function registerUser(payload: RegisterPayload) {
  const { data } = await api.post('/api/auth/register/', payload)
  return data as { access: string; user: unknown }
}
