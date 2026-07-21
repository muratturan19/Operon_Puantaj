import { apiClient } from './apiClient'

export type RaporluPolitikasi = 'tam_ode' | 'hic_odeme' | 'n_gun_esigi'

export interface Sirket {
  id: number
  ad: string
  raporlu_politikasi: RaporluPolitikasi
  raporlu_esik_gun: number
}

export async function sirketGetir(): Promise<Sirket> {
  const { data } = await apiClient.get<Sirket>('/sirket')
  return data
}

export async function sirketGuncelle(payload: {
  raporlu_politikasi?: RaporluPolitikasi
  raporlu_esik_gun?: number
}): Promise<Sirket> {
  const { data } = await apiClient.put<Sirket>('/sirket', payload)
  return data
}
