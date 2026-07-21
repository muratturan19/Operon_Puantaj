export const TR_AYLAR = [
  'OCAK', 'ŞUBAT', 'MART', 'NİSAN', 'MAYIS', 'HAZİRAN',
  'TEMMUZ', 'AĞUSTOS', 'EYLÜL', 'EKİM', 'KASIM', 'ARALIK',
]
export const TR_GUN_KISA = ['Paz', 'Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt'] // getDay(): 0=Paz

// Grid'de Pazar/resmi tatil vurgusu — kullanıcı geri bildirimi (2026-07-04):
// bu günler tüm sütun boyunca net görünür bir kırmızı/pembe olmalı (önceki
// 'warning.50'/'action.hover' karışımı çok soluktu ve başlıkla hücreler
// tutarsızdı). Pazar ve tatil gövde hücrelerinde AYNI tonu paylaşır; başlıkta
// tatil biraz daha koyu + kırmızı yazıyla ayrışır (referans: Puantaj_yeni.html).
export const PAZAR_TATIL_HUCRE_RENGI = '#fef2f2'
export const TATIL_BASLIK_RENGI = '#fde2e2'

// Tema 'divider'ı (#e2e8f0) satır hover/disabled griyle neredeyse aynı tonda —
// fare üzerine gelince veya işten çıkmış personel satırında çizgiler kayboluyor
// (kullanıcı geri bildirimi, 2026-07-04). Grid iç çizgileri için ayrı, her
// arka plana (beyaz/pembe/hover-gri/disabled-gri) karşı görünür kalan bir ton.
export const GRID_CIZGI_RENGI = '#b8c2cf'

export function ymd(yil: number, ay: number, gun: number): string {
  return `${yil}-${String(ay).padStart(2, '0')}-${String(gun).padStart(2, '0')}`
}

export function gunSayisi(yil: number, ay: number): number {
  return new Date(yil, ay, 0).getDate()
}

export function isSunday(yil: number, ay: number, gun: number): boolean {
  return new Date(yil, ay - 1, gun).getDay() === 0
}

// Bir günün, VERİLEN Çalışma Tipi'nin hafta tatili günlerinden biri olup olmadığı
// (kullanıcı geri bildirimi, 2026-07-05: hafta tatili artık HER ZAMAN Pazar değil —
// 5 gün çalışan bir tip için Cumartesi de olabilir). JS Date.getDay() (0=Paz..6=Cmt)
// ile backend'in weekday() kodlaması (0=Pzt..6=Paz) FARKLI — burada dönüştürülür.
export function haftaTatiliMi(haftaTatiliGunleri: number[], yil: number, ay: number, gun: number): boolean {
  const jsGun = new Date(yil, ay - 1, gun).getDay() // 0=Paz..6=Cmt
  const weekday = (jsGun + 6) % 7 // 0=Pzt..6=Paz (Python date.weekday() ile aynı)
  return haftaTatiliGunleri.includes(weekday)
}
