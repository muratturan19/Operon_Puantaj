// Backend Pydantic/SQLModel şemalarıyla eşleşen TS tipleri (app/models, app/api/routes/*)

export interface CalismaTipi {
  id: number
  sirket_id: number
  kod: string
  ad: string
  gunluk_saat: number
  haftalik_gun: number
  hafta_ici_fm_orani: number
  hafta_sonu_fm_orani: number
  resmi_tatil_fm_orani: number
  // Hangi gün(ler) bu tip için hafta tatili sayılır — weekday() ile aynı kodlama (0=Pzt..6=Paz).
  hafta_tatili_gunleri: number[]
  aktif: boolean
}

export interface Personel {
  id: number
  ad_soyad: string
  calisma_tipi_id: number
  maas: number | null // gorebilir_maas_tutari izni yoksa backend null döner (CLAUDE.md §7)
  ng: number
  aktif: boolean // isten_cikis_tarihi'nden türetilir — backend'de ayrı bir alan değil
  ise_baslama_tarihi: string | null
  isten_cikis_tarihi: string | null
}

export interface Donem {
  id: number
  sirket_id: number
  yil: number
  ay: number
  excel_sheet_adi: string | null
  // Bu dönemin varsayılan N.G'si (takvim gün sayısı) — kişi bazlı istisnalar için
  // PersonelOzet.ng'ye bakın (bkz. CHANGELOG Faz 4).
  ng: number
}

export interface Tatil {
  id: number
  sirket_id: number
  tarih: string
  aciklama: string | null
  kaynak: string
}

// Tam gün statüsü — kullanıcı geri bildirimi (2026-07-04). null = normal gün (saatlik izin/FM).
export type GunDurumu = 'devamsiz' | 'yillik_izin' | 'raporlu' | null

export interface PuantajGirisi {
  id: number
  personel_id: number
  donem_id: number
  tarih: string
  gun_durumu: GunDurumu
  izin_saat: number
  fm_saat: number
}

export interface PersonelOzet {
  personel_id: number
  ad_soyad: string
  // Bu dönem için EFEKTİF N.G — kişi bazlı istisna varsa o, yoksa dönemin
  // takvim gün sayısı varsayılanı (Personel.ng ARTIK hesaplamada kullanılmıyor).
  ng: number
  cgun: number
  izin_saat: number
  fm_saat: number
  yillik_izin_gun: number
  raporlu_gun: number
  izin_tl: number | null
  fm_tl: number | null
  // devamsız+raporlu günlerin toplam maaş etkisi — kullanıcı geri bildirimi
  // (2026-07-04): "gelmedi ise maaş eksilmiyor gibi görünüyor" (hesap zaten
  // doğruydu, sadece görünmüyordu).
  gun_maasi_kesintisi: number | null
}

export interface MeResponse {
  id: number
  kullanici_adi: string
  ad_soyad: string
  rol_kod: string
  izinler: Record<string, boolean>
}

export interface HataKaydi {
  id: number
  istek_id: string
  zaman: string
  yol: string
  metod: string
  sorgu: string | null
  kullanici: string | null
  hata_tipi: string
  mesaj: string
  traceback_metni: string | null
}

export interface AuditLogEntry {
  id: number
  aktor_adi: string
  entity_tipi: string
  entity_id: string
  aksiyon: string
  changes: Record<string, { old: unknown; new: unknown }>
  zaman: string
}
