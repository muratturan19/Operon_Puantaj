import { apiClient, setToken } from './apiClient'

export interface SetupStatus {
  kurulum_tamamlandi: boolean
  sirket_adi: string | null
}

export async function getSetupStatus(): Promise<SetupStatus> {
  const { data } = await apiClient.get<SetupStatus>('/setup/status')
  return data
}

export interface SetupCompletePayload {
  sirket_adi: string
  mod: 'tek' | 'cok'
  admin: { kullanici_adi: string; ad_soyad: string; parola: string }
  kullanici_maas_gorebilir: boolean
}

export async function completeSetup(payload: SetupCompletePayload): Promise<void> {
  const { data } = await apiClient.post<{ access_token: string }>('/setup/complete', payload)
  setToken(data.access_token)
}
