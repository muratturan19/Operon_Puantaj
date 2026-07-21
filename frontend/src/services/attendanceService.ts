import { apiClient } from './apiClient'
import type { Donem, GunDurumu, PersonelOzet, PuantajGirisi, Tatil } from './types'

export async function listeleDonemler(): Promise<Donem[]> {
  const { data } = await apiClient.get<Donem[]>('/donemler')
  return data
}

// Get-or-create — dönem seçici henüz Excel'i içe aktarılmamış bir ayı da
// gösterebilsin diye (kullanıcı geri bildirimi 2026-07-04: "temmuz sonuna
// yıllık izin girmek isteyebilir").
export async function donemGetirVeyaOlustur(yil: number, ay: number): Promise<Donem> {
  const { data } = await apiClient.post<Donem>('/donemler', { yil, ay })
  return data
}

export async function listeleGirisler(donemId: number): Promise<PuantajGirisi[]> {
  const { data } = await apiClient.get<PuantajGirisi[]>('/puantaj', { params: { donem_id: donemId } })
  return data
}

export async function ozet(donemId: number): Promise<PersonelOzet[]> {
  const { data } = await apiClient.get<PersonelOzet[]>('/puantaj/ozet', { params: { donem_id: donemId } })
  return data
}

// N.G istisnası — kullanıcı kararı (2026-07-06): varsayılan dönemin takvim gün
// sayısı, kişi bazında SADECE bu dönem için elle değiştirilebilir. ng=null
// istisnayı kaldırıp takvim varsayılanına döner.
export async function personelDonemNgAyarla(
  personelId: number,
  donemId: number,
  ng: number | null,
): Promise<PersonelOzet> {
  const { data } = await apiClient.put<PersonelOzet>(`/puantaj/${personelId}/donem/${donemId}/ng`, { ng })
  return data
}

export interface GirisGuncelle {
  gun_durumu: GunDurumu
  izin_saat: number
  fm_saat: number
}

export async function gunGuncelle(
  personelId: number,
  tarih: string,
  payload: GirisGuncelle,
): Promise<PuantajGirisi | null> {
  const { data } = await apiClient.put<PuantajGirisi | null>(
    `/puantaj/${personelId}/${tarih}`,
    payload,
  )
  return data
}

export async function donemiTemizle(donemId: number): Promise<void> {
  await apiClient.post(`/puantaj/donem/${donemId}/temizle`)
}

export async function listeleTatiller(): Promise<Tatil[]> {
  const { data } = await apiClient.get<Tatil[]>('/tatiller')
  return data
}

export async function tatilEkle(tarih: string, aciklama?: string): Promise<Tatil> {
  const { data } = await apiClient.post<Tatil>('/tatiller', { tarih, aciklama })
  return data
}

export async function tatilSil(tatilId: number): Promise<void> {
  await apiClient.delete(`/tatiller/${tatilId}`)
}
