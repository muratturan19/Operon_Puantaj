# Puantaj Ürünü — Sıfırdan İskele Kurma Talimatı (Build Brief)

> Bu belge, VSCode içindeki kod ajanına (Sonnet 5) verilecek **tek kaynaklı** talimattır.
> Yanında iki dosya gelir; bunları **oku ve doğru kaynak kabul et**:
> - `BESIM.xlsx` — gerçek maaş/puantaj çalışma dosyası (iş mantığının ve Excel çıktısının referansı)
> - `Puantaj.html` — çalışan tek-dosya prototip (UX ve hesap mantığının referansı)
>
> Amaç: Bu prototipi, aşağıdaki mimari ve ilkelerle **kalıcı bir ürün iskeletine** taşımak.
> Prototipteki davranışı birebir koru; sadece altyapıyı ürünleştir.

---

## 0. Çalışma Kısıtları (ZORUNLU)
- **Windows** hedef ortam. Komut/yol örnekleri PowerShell olsun (Linux/mac değil).
- **UTF-8 zorunlu.** Türkçe karakterler (ş, ç, ğ, ı, ö, ü, İ) her katmanda bozulmadan çalışmalı: DB, API, dosya adları, Excel.
- **Veri egemenliği:** Hiçbir veri müşteri ortamından çıkmaz. Bulut yok, dış servis çağrısı yok. Her şey lokal çalışır.
- **Tahmin etme, uydurma.** Emin olmadığın bir kuralda dur ve sor; özellikle bordro hesabında.

---

## 1. Bağlam & Neden
KOBİ'lerde ETA/Logo gibi bir bordro yazılımı olsa bile, "kim kaç gün çalıştı, kim kaç saat izin/mesai yaptı" gibi **girdileri hazırlama** işi hâlâ elle, hatalı Excel'lerde yapılıyor. Bordro yazılımı bir *hesaplama/beyan motoru*; girdiyi hazırlayan **yakalama katmanı** piyasada boş. Bu ürün o boşluğu doldurur.

Gerçek dosyada (`BESIM.xlsx`) tespit edilen ve düzeltilen tipik hatalar (alan bilgisi olarak bil):
- Banka-net formülü satırdan satıra tutarsızdı; bir hücre yanlış satırın icrasına (`Q44`) bakıyordu.
- Toplam satırındaki `SUM` aralıkları eksik/kaymıştı (bazı kişiler toplama girmiyordu).
- Bu ürünün varlık sebebi kısmen budur: elle kurulan Excel **sessizce yanlış maaş ödetir.**

## 2. Ürün Tezi & Konumlandırma
**"ETA'nın yerine geçmiyoruz; ETA'ya girecek temiz, doğru puantajı üreten eksik katmanız."**
- İstila etmeyen (non-invasive): müşterinin mevcut Excel/ETA düzenini değiştirmez, besler.
- Lokal & egemen: maaş en hassas veridir; her şey on-prem çalışır.
- Sıfır kurulum hissi, dakikalar içinde değer.

## 3. Tasarım İlkeleri (Guardrail — her feature kararında uygula)
1. **Günlük kullanıcıya görünmez karmaşıklık.** DB, roller, ETA entegrasyonu gibi şeyler *kurulumcuya/patrona* görünür; puantajı giren kişiye (ör. bir İK/ofis çalışanı) görünmez.
2. **Tek ekran disiplini.** Puantaj gridi her zaman tek, sade ekran kalır. Bir özellik günlük gridi karmaşıklaştırıyorsa hayır.
3. **Esneklik & kolay evrilme.** Şirkete özel kıvrımlar (elden/banka bölüşümü, özel prim) ucuza modellenebilmeli. Kurulum sonrası ilk haftalarda çok sayıda "özel istek/kör nokta" geri bildirimi gelecektir; mimari bu değişimleri **ucuz** kılmalı.
4. **İki rol yeter:** puantajı *giren* ve *onaylayan* (patron). RBAC matrisi kurma.

## 4. Hedef Kullanıcı & Segment
- Segment: 10–200 kişilik, puantajı hâlâ Excel'de tutan KOBİ. Kurumsal değil.
- Günlük kullanıcı: İK/ofis çalışanı (sıfır teknik bilgi varsayımıyla tasarla).
- İkincil: onaylayan/patron.

---

## 5. İŞ MANTIĞI — Bordro Hesap Kuralları (birebir uygula, `Puantaj.html` ile aynı)
Aylık, **30 gün (N.G) tabanlı** net puantaj. Kişi bazında:

```
saatlik_ücret = (MAAŞ / N.G) / 7.5        # N.G çoğunlukla 30; günde 7,5 saat
Ç.GÜN         = N.G − (tam_gün_devamsızlık_sayısı)   # min 0
G (gün maaşı) = (MAAŞ / N.G) × Ç.GÜN

# Saatlik izin (birim: saat) — hak edişten düşülür (1,0×)
İZİN.TL       = toplam_izin_saati × saatlik_ücret

# Fazla mesai (birim: saat) — iki kademe; izin ile KARIŞMAZ, ayrı kova
#   hafta içi (Pzt–Cmt, tatil değil)  → ×1,5
#   Pazar VEYA resmi tatil            → ×2
FM.TL         = Σ_gün( fm_saat_gün × saatlik_ücret × (pazar_veya_tatil ? 2 : 1,5) )

HAKEDİŞ       = PRİM + FM.TL + G − İZİN.TL
BANKA_net     = TOPLAM − AVANS − İCRA − BES        # TOPLAM = HAKEDİŞ + AGİ(0)
```

Notlar:
- Tam gün devamsızlık → **Ç.GÜN**'e (E). Saatlik izin → ayrı **İZİN.SAAT** kolonuna. Çift düşüş olmaz.
- FM iki kademeli; prototipte Excel'e **tek "FM tutarı" (₺)** olarak yazılıyor (kullanıcı kararı). Üründe de böyle: `K = FM.TL` (hesaplı değer), `J = FM.SAAT` (bilgi amaçlı toplam saat).
- AGİ kaldırıldı → 0.

### Doğrulanmış test vakaları (kabul kriteri olarak kullan)
- Kişi maaş 32000, N.G 30 → saatlik = 142,2222
  - 4 saat FM hafta içi (×1,5) = 853,33
  - 3 saat FM Pazar (×2) = 853,33 → **FM.TL = 1.706,67**
  - 2 saat izin → **İZİN.TL = 284,44**
- Kişi maaş 50000, 2 gün devamsız → **Ç.GÜN = 28**, G = 46.666,67
- Tatil örneği: 19 Mayıs (resmi tatil), 5 saat FM ×2, saatlik 142,2222 → 1.422,22

### 2026 TR resmi tatilleri (gömülü + düzenlenebilir; Pazar zaten otomatik ×2)
`2026-01-01, 2026-03-20, 2026-03-21, 2026-03-22, 2026-04-23, 2026-05-01, 2026-05-19, 2026-05-27, 2026-05-28, 2026-05-29, 2026-05-30, 2026-07-15, 2026-08-30, 2026-10-29`

---

## 6. Excel Alan Bilgisi (BANKA sayfası kolon haritası — çıktı hedefi)
Güncellenmiş BANKA sayfası düzeni (veri satırı formülleri):
```
A no | B AD SOYAD | C MAAŞ | D N.G | E Ç.GÜN | F Y.TL(=C/D) | G MAAŞ(=F*E)
H M.1(=F/7.5) | I M.1.5(=H*1.5) | J FM.SAAT | K FM.TL | L İZİN.SAAT | M İZİN.TL(=L*H)
N PRİM | O HAKEDİŞ(=N+K+G-M) | P AVANS | Q AGİ | R TOPLAM(=O+Q)
S İCRA | T BES | U BANKA(=R-P-S-T) | V ETA | W FARK(=V-U)
```
- Yaz: sadece `E`, `L`, `J`, `K` (kişi başına). Gerisi formül; V(ETA)/W(FARK) mutabakat için kalır.
- `ELDEN` sayfaları farklı ve tutarsız yapıda; **DOKUNMA** (ayrı bir iş, kapsam dışı). Sadece `BANKA` sayfalarını işle.
- Diğer tüm sayfalar/formüller/biçimler korunmalı (round-trip fidelity).

---

## 7. UX Spesifikasyonu (referans: `Puantaj.html` ve PlannerWS Takvim ekranı)
- **Aylık takvim gridi.** Satır = personel (ad + maaş), sütun = ayın günleri (gün no + kısa gün adı). Sticky ilk sütun (isim) + sticky sağ özet sütunları.
- **Sol tık** = o gün "gelmedi" (kırmızı, tam gün devamsızlık). Tekrar tık geri alır.
- **Sağ tık** = popover: `İzin (saat)` ve `Fazla mesai (saat)` girişi + o günün FM oranını (×1,5 / ×2) gösterir.
- **Sağ özet sütunları (canlı):** `Ç.GÜN · İzin s · İzin ₺ (kırmızı, −) · FM s · FM ₺ (mavi)`.
- **Tatil editörü:** resmi tatilleri ekle/çıkar (×2 için).
- **Ay geçişi:** ay seçilince o ayın gridi çizilir; her ayın verisi ayrı saklanır, kaybolmaz.
- Renkler/his: PlannerWS dili — marka turuncusu `#f47c20`, slate paleti. `Puantaj.html`'deki görünümü koru.

---

## 8. Mimari (ürünleştirme hedefi)
Mevcut kolektif360/PlannerWS stack'i ile hizala:
- **Frontend:** React 19 + TypeScript + MUI v6. (PlannerWS bileşen dili ile uyumlu.)
- **Backend:** FastAPI + Pydantic (lokal, `127.0.0.1`).
- **DB:** Lokal **SQLite** (dosya tabanlı, on-prem). Kullanıcıya görünmez.
- **Paketleme (opsiyonel, MVP sonrası):** PlannerWS gibi Electron ile masaüstü .exe.
- **Excel I/O:** Backend'de **openpyxl** ile oku/yaz — biçim ve formülleri **birebir** korur (prototipte ExcelJS round-trip kanıtlandı; üründe openpyxl daha güvenli). "Aktar" tek buton → backend openpyxl çağırır.
- **Auth:** minimal, 2 rol (giren / onaylayan). Lokal, basit.

## 9. Veri Modeli (SQLite — önerilen şema)
```
Personel(id, ad, maas, ng=30, aktif=true)
Donem(id, yil, ay)                              # ör. 2026-06
PuantajGiris(id, personel_id, tarih,            # tek gün
             absent bool, izin_saat real, fm_saat real)
Tatil(id, tarih)                                 # resmi tatiller
Kullanici(id, ad, rol['giren'|'onaylayan'], parola_hash)
Ayar(anahtar, deger)                             # çalışma günleri, vb.
```
Hesaplar türetilir (saklanmaz): Ç.GÜN, İZİN.TL, FM.TL, HAKEDİŞ hep kurallardan hesaplanır.

## 10. Import / Export
- **Import (roster):** Mevcut `BESIM.xlsx` `BANKA` sayfasından personel + maaş çek (openpyxl). Alternatif: uygulama içinde yönet.
- **Export:** Seçili ay(lar)ın `BANKA` sayfasına `E, L, J, K` yaz; diğer her şeyi koru. Tek export **işaretli tüm ayları** yazsın (prototipteki gibi).

## 11. Non-Goals (net sınırlar — kapsama alma)
- SGK/vergi/net **bordro hesaplamıyoruz** (onu ETA yapar). Biz girdiyi üretiriz.
- Bordro yazılımının yerine geçmiyoruz.
- MVP'de bulut / çok-kiracılı SaaS / mobil yok.
- `ELDEN` sayfalarına dokunma.

## 12. MVP Kapsamı (fazlar)
- **Faz 1 (iskele):** React+MUI grid + FastAPI + SQLite + hesap kuralları + BESIM import/export (openpyxl). Prototiple birebir davranış.
- **Faz 2:** 2 rol auth, tatil yönetimi, çoklu ay, yıllık izin bakiyesi (opsiyonel).
- **Faz 3:** ETA'ya doğrudan aktarım, Electron paketleme, denetim/log.

## 13. Kabul Kriterleri & Doğrulama
- Bölüm 5'teki **doğrulanmış test vakaları** birebir tutmalı (1.706,67 / 284,44 / 28 gün / 1.422,22).
- Export sonrası: `BESIM.xlsx`'in tüm sayfaları, formülleri, sayı biçimleri ve Türkçe karakterleri **bozulmadan** korunmalı. (LibreOffice/Excel ile recalc edip değerleri karşılaştır.)
- FM ile izin **karışmamalı** (6 saat FM + 6 saat izin → net +0,5×6×saatlik).
- İzin=0 olan mevcut aylarda banka tutarları **değişmemeli** (regresyon).
- UTF-8 / Windows uyumu.

## 14. Kod Güvencesi (ürünleşince)
Maaş verisi işleyen bir üründür. Kurulumdan önce: birim testler (hesap kuralları), veri-akışı/güvenlik dikişlerinin (dosya erişimi, yetki sınırı, girdi doğrulama) gözden geçirilmesi, ve mümkünse bağımsız bir teknik göz. "Çapraz-YZ kontrolü" gerekli ama sistem seviyesinde tek başına yeterli değildir.

---

### Ajana ilk komut (özet)
> "Ekteki `BESIM.xlsx` ve `Puantaj.html`'i oku. Bu brief'teki mimari (React 19 + TS + MUI v6 / FastAPI + Pydantic / lokal SQLite) ile Faz 1 iskeletini kur. İş mantığını Bölüm 5'ten birebir uygula ve Bölüm 13 test vakalarıyla doğrula. `ELDEN` sayfalarına dokunma. Windows + UTF-8. Emin olmadığın bordro kuralında dur ve sor."
