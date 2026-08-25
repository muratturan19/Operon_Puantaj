import { apiClient } from './apiClient'

export interface SurumBilgisi {
  surum: string
  tarih: string
  ad: string
}

export async function surumGetir(): Promise<SurumBilgisi> {
  const { data } = await apiClient.get<SurumBilgisi>('/surum')
  return data
}
