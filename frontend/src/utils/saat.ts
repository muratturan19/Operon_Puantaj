/**
 * utils/saat.ts — İzin/FM saatlerinin gösterimi ve "yarım gün" karşılığı.
 *
 * Müşteri geri bildirimi (2026-08-25): "yarım gün izin verirken 3 deseler az,
 * 4 deseler fazla oluyor." Günlük çalışma 7,5 saat olduğu için yarım gün 3,75
 * saattir; elle yazılması zahmetli ve yuvarlama hatasına açık. Sabit 3,75
 * DEĞİL, çalışma tipinin `gunluk_saat`'inin yarısı kullanılır — 8 saatlik bir
 * tip tanımlanırsa yarım gün kendiliğinden 4 saat olur.
 */

export const VARSAYILAN_GUNLUK_SAAT = 7.5

export function yarimGunSaati(gunlukSaat: number = VARSAYILAN_GUNLUK_SAAT): number {
  return Math.round((gunlukSaat / 2) * 100) / 100
}

export function yarimGunMu(saat: number, gunlukSaat: number = VARSAYILAN_GUNLUK_SAAT): boolean {
  return saat > 0 && saat === yarimGunSaati(gunlukSaat)
}

/** 3.75 → "3,75" · 4 → "4" (Türkçe ondalık ayırıcı, gereksiz sıfır yok). */
export function saatMetni(saat: number): string {
  return saat.toLocaleString('tr-TR', { maximumFractionDigits: 2 })
}
