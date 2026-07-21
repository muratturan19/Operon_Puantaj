import { apiClient } from './apiClient'

export interface Rol {
  id: number
  kod: string
  ad: string
  izinler: Record<string, boolean>
}

export interface Kullanici {
  id: number
  kullanici_adi: string
  ad_soyad: string
  email: string | null
  rol_id: number
  aktif: boolean
}

export async function listeleRoller(): Promise<Rol[]> {
  const { data } = await apiClient.get<Rol[]>('/roller')
  return data
}

export async function listeleKullanicilar(): Promise<Kullanici[]> {
  const { data } = await apiClient.get<Kullanici[]>('/kullanicilar')
  return data
}

export async function kullaniciOlustur(payload: {
  kullanici_adi: string
  ad_soyad: string
  email?: string
  parola: string
  rol_id: number
}): Promise<Kullanici> {
  const { data } = await apiClient.post<Kullanici>('/kullanicilar', payload)
  return data
}

export async function kullaniciGuncelle(
  id: number,
  payload: { ad_soyad?: string; email?: string | null; rol_id?: number; aktif?: boolean },
): Promise<Kullanici> {
  const { data } = await apiClient.put<Kullanici>(`/kullanicilar/${id}`, payload)
  return data
}

export async function parolaDegistir(id: number, yeniParola: string): Promise<void> {
  await apiClient.post(`/kullanicilar/${id}/parola-degistir`, { yeni_parola: yeniParola })
}
