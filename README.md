# Operon Puantaj

> "ETA'nın yerine geçmiyoruz; ETA'ya girecek temiz, doğru puantajı üreten eksik katmanız."

Puantajını hâlâ Excel'de tutan 10–200 kişilik şirketler için, mevcut Excel düzenini değiştirmeden
çalışan bir puantaj/bordro-girdi yakalama aracı. Sıfır teknik bilgili İK/ofis çalışanının günlük
kullanacağı tek bir takvim/grid ekranı üzerinden devamsızlık, yıllık izin, raporlu ve fazla mesai
işaretlenir; gün maaşı kesintisi, izin ve fazla mesai tutarları anlık hesaplanır. Şirket, kolektif360
(Operon) ürün ailesinin bir parçasıdır.

## Takvim/Grid Ekranı

Ürünün korunması gereken tek sabit unsuru: tek ekranlı, sıfır-eğitimli bir grid deneyimi.

- **Sol tık** → o gün için devamsızlık işaretler/kaldırır.
- **Sağ tık** → İzin (saat bazlı)/Fazla Mesai (saat bazlı)/Yıllık İzin (tam gün)/Raporlu (tam gün)
  popover'ı açar. Bir günde ya tam-gün statüsü ya saatlik izin/FM olur, ikisi birlikte olmaz.
- **12 aylık dönem seçici** — henüz Excel'i içe aktarılmamış aylar da "(yeni)" etiketiyle
  seçilebilir (ör. Temmuz sonuna erken yıllık izin girmek için); seçildiğinde dönem sessizce
  oluşturulur.
- **Canlı özet kolonları** — Ç.GÜN, Gün Kesintisi (₺), Yıllık İzin (gün), Raporlu (gün), İzin
  (saat/₺), FM (saat/₺) — hepsi server tarafında hesaplanır, tek doğruluk kaynağı budur.
- Personel, işe giriş/çıkış tarihine göre ay bazlı görünür (işten çıkan kişi çıktığı ayın sonuna
  kadar listede kalır); ay içinde işe girişten önceki/çıkıştan sonraki gün hücreleri devre dışıdır.
- Puantaj girişi yapan ama denetim kaydını göremeyen kullanıcılara, işlemlerin kayıt altında
  olduğunu açıkça belirten bir bilgi notu gösterilir.

## Bordro Hesap Kuralları

```
saatlik_ücret = (MAAŞ / N.G) / günlük_saat
Ç.GÜN         = N.G − işe_dışı_gün − devamsız_gün − raporlu_düşen_gün        (min 0)
gün_maaşı     = (MAAŞ / N.G) × Ç.GÜN

İZİN.TL       = toplam_izin_saati × saatlik_ücret

FM.TL         = Σ_gün( fm_saat_gün × saatlik_ücret × (pazar/tatil ? hafta_sonu_oranı : hafta_içi_oranı) )
                # izin ile karışmaz, ayrı kova

HAKEDİŞ       = PRİM + FM.TL + gün_maaşı − İZİN.TL
```

- **Yıllık İzin** Ç.GÜN'den hiç düşmez, tam ödenir.
- **Raporlu**'nun Ç.GÜN etkisi şirket genelinde ayarlanabilir bir politikadır: Tam Öde / Hiç Ödeme
  (varsayılan) / N Gün Eşiği (her ardışık rapor bloğunun ilk N günü ödenir, kalanı düşer — "belli
  bir günün üzerini SGK ödüyor" varsayımı).
- **Kısmi ay maaşı** — ay ortasında işe giren/çıkan personelin Ç.GÜN'ü işe giriş/çıkış tarihine
  göre otomatik prorate edilir.
- **FM oranları** (varsayılan hafta içi ×1,5 / hafta sonu-tatil ×2) Çalışma Tipi bazında
  ayarlanabilir.

## Parametrizasyon — "Çalışma Tipi"

Şirket, "+Ekle" ile çalışma tipleri tanımlar (varsayılan: Beyaz Yaka, Mavi Yaka — çoğu şirkette
zaten var; istenirse "Müdür" gibi ek tipler de eklenebilir). Her tipin kendi parametreleri olur:

- Günlük çalışma saati, haftalık çalışma günü.
- Fazla mesai çarpanları (hafta içi / hafta sonu-tatil).

Personel bir tipe atanır; müşterinin Excel'inde bu tipi belirten bir kolon varsa mapping onu okur,
yoksa şirket geneli bir varsayılan tipe düşülür.

Ayrıca **Şirket Ayarları** sayfasından şirket genelinde Raporlu ödeme politikası ayarlanır.

## Roller ve İzinler

Genişletilebilir bir rol/izin modeli (`Rol.izinler` — serbest JSON, yeni bir izin eklemek
migrasyon gerektirmez). Varsayılan üçlü:

| Rol | Görür mü | Yazar mı |
|---|---|---|
| **Admin** | Her şey | Her şey |
| **Kullanıcı** | Sadece puantaj; maaş görünürlüğü Admin'in kararına bağlı (varsayılan gizli) | Sadece puantaj girişi |
| **GM** | Her şey (maaş dahil) | Hiçbir şey — export/rapor indirme hariç |

İlk kurulumda **Kurulum Sihirbazı** şu soruları sırayla sorar: Tek Kullanıcı mı Çok Kullanıcı mı,
kurulum modu, Admin hesabı, (Çok Kullanıcı ise) "Kullanıcı rolü maaş tutarlarını görebilsin mi?"
Kurulum tamamlanmadan login ekranı bile gösterilmez.

Sonradan bir kullanıcının rolü/durumu (aktif-pasif) değiştirilebilir, şifresi sıfırlanabilir —
Admin kendi hesabını pasife alamaz.

## Güvenlik ve Şeffaflık

- **`/güvenlik` sayfası** — tüm parametre değişiklikleri ve puantaj girişleri, kim/ne zaman/ne
  değişti bilgisiyle (append-only denetim kaydı) admin ve maaş görebilen role gösterilir.
- Maaş tutarı içeren her çıktı (Excel export, denetim kaydı) `gorebilir_maas_tutari` izni olmadan
  tamamen kapalıdır — bu iki izin, kendi asıl izninden (export/denetim) bağımsız olarak da
  kilitlidir, rastlantısal izin eşleşmesine güvenilmez.
- Müşteri maaş verisiyle üretim ortamında **hiçbir LLM/relay çağrısı yapılmaz** — mapping,
  onboarding sırasında bir kereye mahsus insan+Claude konuşmasıyla üretilip statik bir config
  olarak yüklenir.

## Excel Entegrasyonu

Müşterinin Excel dosyasıyla içe/dışa aktarım, ürünün temel ve her zaman açık olan yeteneğidir.
Mapping-tabanlı bir adaptör mimarisi kullanılır — müşterinin Excel düzeni hiçbir zaman koda
hardcode edilmez:

- **İçe aktarım**: personel listesi, maaş, N.G, çalışma tipi vb. müşterinin kendi Excel'inden
  okunur (kolon eşlemesi mapping config'ten gelir).
- **Dışa aktarım**: yalnızca o dönem en az bir girişi olan personelin hücrelerine dokunulur —
  dokunulmayan personel "o ay eksik çalışma da mesai de yok, tam maaşını aldı" demektir.
- Onboarding'de yeni bir müşteri Excel'i geldiğinde `backend/scripts/excel_kesif.py` ile sheet
  listesi, header adayları ve ham örnek satırlar otomatik-tahminsiz dökülür; mapping kararını
  hâlâ insan+Claude konuşması verir.

**ETA'ya (veya Logo, Netsis, Mikro gibi başka bir bordro/muhasebe programına) doğrudan aktarım
teknik olarak mümkündür** — aynı mapping mekanizması, hedef programın beklediği kolon/sayfa
düzenine göre yazan bir export şablonu tanımlamaya zaten uygundur. Bu, **proaktif sunulan genel
bir özellik değildir** — yalnızca belirli bir müşteri özellikle talep ederse eklenir.

## Mimari

- **Backend**: FastAPI + SQLModel + Alembic, PostgreSQL (hem on-prem hem SaaS'ta).
- **Frontend**: React 19 + TypeScript + MUI v6, route bazlı code-splitting.
- **Auth**: on-prem modda yerel kullanıcı adı/şifre (JWT); SaaS modda Portal SSO (RS256 JWT) —
  kimlik doğrulama adaptörü değişir, iç rol/izin modeli iki modda da aynı kalır.
- **Çok kiracılılık**: aynı şirket içinde farklı yetkideki kullanıcılar; tenant izolasyonu DB
  seviyesinde (her kurulum/tenant kendi veritabanına sahiptir).
- **Dağıtım**: on-premise (Windows, native PostgreSQL servisi) veya SaaS (Portal + Traefik +
  tenant-başına-DB) — uygulama kod tabanı ortak, paketleme farklı.

Mimari kararlar ve gerekçeleri için [`CLAUDE.md`](CLAUDE.md); ertelenen/planlanan işler için
[`ROADMAP.md`](ROADMAP.md); sürüm geçmişi için [`CHANGELOG.md`](CHANGELOG.md).

## Geliştirme

```
backend/   # FastAPI + SQLModel + Alembic
  app/
    models/       # SQLModel tabloları
    services/     # Saf iş mantığı (payroll_calc, excel_adapter, personel_filtre, ...)
    api/routes/   # FastAPI endpoint'leri
  scripts/        # Onboarding/keşif araçları (excel_kesif.py)
  tests/          # pytest
frontend/  # React 19 + TypeScript + MUI v6
  src/
    pages/        # Sayfa bileşenleri
    components/   # Paylaşılan bileşenler (grid, popover, ...)
    services/     # API istemcileri
```

```bash
# Backend
cd backend
python run.py                    # geliştirme sunucusu (http://127.0.0.1:8020)
python -m pytest tests/          # test paketi

# Frontend
cd frontend
npm run dev                      # geliştirme sunucusu (http://localhost:5174)
npm run build                    # production build (tip kontrolü dahil)
```
