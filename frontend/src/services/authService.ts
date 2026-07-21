import { apiClient, setToken } from './apiClient'
import type { MeResponse } from './types'

export async function login(kullaniciAdi: string, parola: string): Promise<void> {
  const form = new URLSearchParams()
  form.set('username', kullaniciAdi)
  form.set('password', parola)
  const { data } = await apiClient.post('/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  setToken(data.access_token)
}

export async function me(): Promise<MeResponse> {
  const { data } = await apiClient.get<MeResponse>('/auth/me')
  return data
}

export async function ssoLogout(): Promise<void> {
  await apiClient.post('/sso/logout')
}
