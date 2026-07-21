import { apiClient } from './apiClient'
import type { CalismaTipi, Personel } from './types'

export async function listelePersonel(): Promise<Personel[]> {
  const { data } = await apiClient.get<Personel[]>('/personel')
  return data
}

export async function personelOlustur(payload: {
  ad_soyad: string
  calisma_tipi_id: number
  maas: number
  ng: number
  ise_baslama_tarihi?: string | null
}): Promise<Personel> {
  const { data } = await apiClient.post<Personel>('/personel', payload)
  return data
}

export async function personelGuncelle(id: number, payload: Partial<Personel>): Promise<Personel> {
  const { data } = await apiClient.put<Personel>(`/personel/${id}`, payload)
  return data
}

export async function listeleCalismaTipleri(): Promise<CalismaTipi[]> {
  const { data } = await apiClient.get<CalismaTipi[]>('/calisma-tipleri')
  return data
}

export async function calismaTipiOlustur(payload: {
  kod: string
  ad: string
  gunluk_saat: number
  haftalik_gun: number
  hafta_tatili_gunleri?: number[]
}): Promise<CalismaTipi> {
  const { data } = await apiClient.post<CalismaTipi>('/calisma-tipleri', payload)
  return data
}

export async function calismaTipiGuncelle(id: number, payload: Partial<CalismaTipi>): Promise<CalismaTipi> {
  const { data } = await apiClient.put<CalismaTipi>(`/calisma-tipleri/${id}`, payload)
  return data
}
