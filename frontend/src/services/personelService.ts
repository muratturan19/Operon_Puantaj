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

export interface MaasGecmisiKaydi {
  id: number
  yil: number
  ay: number
  maas: number
  created_at: string
}

// `maas` artık PersonelUpdate'te yok (kullanıcı sorusu, 2026-07-06: zam geçmiş
// dönemleri bozmasın) — tüm maaş değişiklikleri bu uç nokta üzerinden, etkin
// olduğu (yıl,ay) belirtilerek yapılır.
export async function zamGir(personelId: number, yil: number, ay: number, maas: number): Promise<Personel> {
  const { data } = await apiClient.post<Personel>(`/personel/${personelId}/zam`, { yil, ay, maas })
  return data
}

export async function listeleMaasGecmisi(personelId: number): Promise<MaasGecmisiKaydi[]> {
  const { data } = await apiClient.get<MaasGecmisiKaydi[]>(`/personel/${personelId}/maas-gecmisi`)
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
