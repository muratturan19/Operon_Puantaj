import type { Personel } from '../services/types'
import { gunSayisi } from './date'

// Backend'deki app/services/personel_filtre.py::donemde_calisiyor_mu ile birebir
// aynı mantık — işten çıkan personel çıktığı ayın sonuna kadar listede kalır,
// yeni giren personel işe başladığı aydan itibaren görünür.
export function donemdeCalisiyorMu(p: Personel, yil: number, ay: number): boolean {
  const donemBaslangic = `${yil}-${String(ay).padStart(2, '0')}-01`
  const donemBitis = `${yil}-${String(ay).padStart(2, '0')}-${String(gunSayisi(yil, ay)).padStart(2, '0')}`

  if (p.ise_baslama_tarihi && p.ise_baslama_tarihi > donemBitis) return false
  if (p.isten_cikis_tarihi && p.isten_cikis_tarihi < donemBaslangic) return false
  return true
}

// Bir ay içinde görünen personelin, o AYIN İÇİNDEKİ belirli bir güne puantaj
// girilebilir mi (işe henüz başlamamış / zaten ayrılmış günler devre dışı).
export function gunCalisiyorMu(p: Personel, tarih: string): boolean {
  if (p.ise_baslama_tarihi && tarih < p.ise_baslama_tarihi) return false
  if (p.isten_cikis_tarihi && tarih > p.isten_cikis_tarihi) return false
  return true
}
