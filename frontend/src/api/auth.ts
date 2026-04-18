import api from '@/lib/axios'

export interface RegisterPayload {
  username: string
  email: string
  password: string
  password2: string
  home_currency: string
}

export interface RegisteredUser {
  id: number
  username: string
  email: string
  home_currency: string
  display_name: string
  total_cash: string
}

export async function registerUser(payload: RegisterPayload) {
  const { data } = await api.post('/api/auth/register/', payload)
  return data as RegisteredUser
}

export async function requestPasswordReset(email: string): Promise<void> {
  await api.post('/api/auth/password/reset/', { email })
}

export async function verifyPasswordResetOTP(email: string, otp: string): Promise<void> {
  await api.post('/api/auth/password/reset/verify/', { email, otp })
}

export async function confirmPasswordReset(
  email: string,
  otp: string,
  new_password: string,
  new_password2: string
): Promise<void> {
  await api.post('/api/auth/password/reset/confirm/', { email, otp, new_password, new_password2 })
}
