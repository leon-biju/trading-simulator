import api from '@/lib/axios'

export interface UpdateProfilePayload {
  display_name?: string
  home_currency?: string
}

export interface ChangePasswordPayload {
  current_password: string
  new_password: string
  new_password2: string
}

export async function updateProfile(payload: UpdateProfilePayload): Promise<void> {
  await api.patch('/api/users/me/', payload)
}

export async function changePassword(payload: ChangePasswordPayload): Promise<void> {
  await api.post('/api/auth/password/change/', payload)
}
