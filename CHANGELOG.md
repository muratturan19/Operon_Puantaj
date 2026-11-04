# Changelog — Operon Puantaj

> Bu dosya, `CLAUDE.md`/`ROADMAP.md`'deki karar kayıtlarının kronolojik özetidir.
> Format [Keep a Changelog](https://keepachangelog.com/) ilkelerinden esinlenir, Türkçe.
> Her girişin *neden*i için `CLAUDE.md`, açık/kapalı roadmap kalemleri için `ROADMAP.md`'ye bakın.
>
> **Sürümleme (2026-08-25'te tanımlandı):** buradaki "Faz" numarası sürümün MAJOR.MINOR'ıdır
> (Faz 4.9 → `4.9.x`), PATCH aynı faz içindeki düzeltmeleri sayar. Sürüm iki yerde sabittir ve
> birlikte güncellenir: `backend/app/core/version.py` ve `frontend/src/config/surum.ts`.
> Canlıdaki sürüm `GET /api/surum` ile sorulabilir, arayüzde sağ üstteki rozette görünür.

## [4.9.7] — 2026-11-04

**Neden:** ServerCare (bakım programı) güvenlik güncellemelerini bu uygulamaya kendisi yayınlayabilsin diye sürümü depodaki `VERSION` dosyasından okur; her bakım yayınında sürüm bir artırılır ve CHANGELOG'a kayıt düşülür.

- Kökte `VERSION` dosyası eklendi (`4.9.7`). Uygulama kodu değişmedi.

## [4.9.6] — 2026-10-26 (arayüz: SaaS'ta oturum yoksa şifre formu yerine Portal'a yönlendirme)

26 Ekim'de, 4.9.5'te düzeltilen giriş hatası sürerken bir kullanıcı karşısına çıkan eski şifre
formuna kullanıcı adı ("2026-7") ve şifre yazdı, "Kullanıcı adı veya şifre hatalı" gördü ve ne
yapacağını bilemedi. SaaS modda (`AUTH_MODE=saas`) bu form hiçbir zaman çalışamaz: yerel giriş
(`POST /api/auth/login`) bilerek kapalıdır, 404 döner; arayüz ise girişteki her hatayı
"Kullanıcı adı veya şifre hatalı" diye gösteriyordu. Oturum yalnız Portal SSO'dan gelir. SSO
çerezi yoksa ya da `/api/auth/me` 401 dışında bir hata verirse (bakım sonrasındaki 500 gibi)
kullanıcı `/login`'e düşüyor ve bu kullanılamaz formu görüyordu.

### Değişenler

- `pages/LoginPage.tsx`: SaaS derlemesinde (`VITE_AUTH_MODE=saas`, Dockerfile) şifre formu hiç
  gösterilmez. Yerine aynı "Operon Puantaj" kartında **"Oturumunuz bulunamadı"** başlığı,
  girişin Kolektif360 portalı üzerinden yapıldığını anlatan kısa bir metin ve Portal'ın
  uygulama listesine (`PORTAL_APPS_URL`, oturum düşünce zaten kullanılan adres) giden
  **"Portala git"** düğmesi çıkar. Mod derleme anında bilindiği için sunucuya ek istek
  atılmaz: oturum bozukken backend'in kendisi de hata veriyor olabilir.
- On-prem derlemede kullanıcı adı/şifre formu ve hata mesajı değişmedi.
- Backend değişmedi (yalnız sürüm numarası).

## [4.9.5] — 2026-10-26 (düzeltme: bakımdan sonra kimse giriş yapamıyordu)

24 Ekim bakımında imaj yeniden derlenince `sqlmodel` 0.0.48'e çıktı. Bu sürüm saat dilimsiz
`datetime` değerini veritabanına yazarken reddediyor. Portal girişinde `last_login =
datetime.utcnow()` her seferinde 500 verdi; arayüz bu yüzden eski şifre formuna düştü ve
kullanıcılar "Kullanıcı adı veya şifre hatalı" gördü. Hatanın kendisi de `error_log`'a aynı
sebeple yazılamadı (yalnız konteyner logunda görünüyordu). Portal 9 Ekim'de aynı sorunu yaşamıştı.

### Değişenler

- DB'ye yazılan "şimdi" değeri tek yerden gelir: `app/core/zaman.py` → `simdi_utc()`
  (saat dilimli UTC). Tüm model varsayılanları (`created_at`, `zaman`) ve atamalar
  (`last_login`, `updated_at`) buna çevrildi. Sütunlar `timestamp without time zone`;
  DB oturumu UTC olduğu için saklanan saat öncekiyle aynı, şema değişikliği yok.
- `tests/test_datetime_awareness.py`: tablo varsayılanları saat dilimli mi, gerçek ORM
  yazma/okuma turu, kaynakta `datetime.utcnow` geri gelirse test kırılır.

## [4.9.4] — 2026-10-23 (güvenlik: JWT kütüphanesi python-jose → PyJWT)

Bileşen taramasında (AIAssay Web) üretim imajındaki `python-jose 3.5.0` için **kritik**
bir açık çıktı: GHSA-3qf3-8w2g-rqmx — DER kodlu açık anahtarlarla algoritma karışıklığı
korumasının atlatılması. Düzeltilmiş sürümü yok; beraberinde gelen `ecdsa 0.19.2`'de de
düzeltmesi olmayan bir zamanlama açığı (Minerva) var. Kütüphane bu yüzden tamamen
bırakıldı, yerine `PyJWT[crypto]` geldi (Operon_RolFit'te aynı geçiş canlıda).

### Değişenler

- **Portal SSO doğrulaması** (`services/portal_sso_service.py`) yalnız RS256 kabul eder;
  `aud`, `iss` ve `exp` denetlenir, `exp/iat/aud/iss/sub` claim'lerinden biri eksik jeton
  reddedilir, portal ile saat kayması için 10 sn pay bırakılır. Portal anahtarı artık
  yalnız **imza** tutmadığında yeniden çekilir (anahtar dönmüş olabilir); süresi dolmuş ya
  da başka uygulamaya kesilmiş bir jeton portal'a gereksiz istek attırmaz. Anahtar
  tazelenirken portal'a ulaşılamazsa 500 yerine 401 döner.
- **Kendi (on-prem) oturum jetonlarımız** (`core/security.py`) aynı HMAC algoritmasıyla
  (`JWT_ALGORITHM`, varsayılan HS256) imzalanmaya devam eder; `JWT_ALGORITHM` artık yalnız
  HS256/HS384/HS512 olabilir (`none` ya da asimetrik algoritma seçilemez). `exp` ve `sub`
  zorunlu; sayısal olmayan bir `sub` 500 yerine 401 verir.
- `sub` zaten string (`"12"`) yazılıyordu; PyJWT 2.10+ bunu şart koştuğu için davranış
  değişmedi. **Yeniden giriş gerekmez** — eski jetonlar da string `sub` taşıdığı için
  geçerli kalır.
- Arayüz bağımlılıkları kendi sürüm aralıkları içinde güncellendi: `axios` 1.18.1 → 1.20.0,
  `follow-redirects` 1.16.0 → 1.16.1, `react-router(-dom)` 7.18.1 → 7.18.4.
  `package-lock.json` yalnız bu paketlerin kayıtlarında değişti (npm 11'in `update`'i,
  Docker'daki npm 10'un `ci`'ı için gereken isteğe bağlı kayıtları siliyordu).

### Doğrulama

- `pytest` 67/67 yeşil (50 mevcut + 17 yeni `tests/test_portal_sso_jwt.py`): gerçek RS256
  jetonlarla geçerli jeton geçer; yanlış `aud`/`iss`, süresi dolmuş, `sub`/`aud`/`iat`
  eksik, yabancı anahtarla imzalı, açık anahtarla HS256 sahtesi ve `alg: none`
  reddedilir. Kendi jetonumuz üret → doğrula turunda string `sub` int kullanıcı id'sine
  döner; int `sub`, süresi dolmuş, `exp`'siz, yanlış sırla imzalı ve `alg: none` jeton 401.
- `npm ci` (npm 10 ve 11) ve `npm run build` başarılı.

## [4.9.3] — 2026-09-01 (KRİTİK: satır silme formül hizasını bozuyordu — 4.9.1 regresyonu)

Müşteri geri bildirimi: *"değer olarak görünüyor personeller listenin alt kısmında, bi de
mesela şennura çalışılan gün ekliyorum benim satırımda hesaplama yapıyor."*
**Bu, aynı gün 4.9.1 ile eklenen "ayrılmış personeli sayfadan çıkar" özelliğinin yan
etkisiydi — kendi ürettiğimiz bir regresyon.**

### Düzeltilenler

- **`openpyxl.delete_rows()` / `insert_rows()` formül METNİNİ değiştirmez.** Hücreleri
  taşırlar ama `=C46/D46` yazan bir formül, satır 44'e kaysa bile `=C46/D46` kalır. 4.9.1'de
  5 ayrılmış personelin satırı silinince altındaki **29 satırın formülleri bir/iki satır
  aşağıyı** göstermeye başladı: ŞENNUR BOBİÇ 44. satıra kaydı ama hâlâ 46. satırı (FİKRİYE
  BULUT) hesaplıyordu, EMİNE TURAN 41. satırdan 42'yi (CANSEL ŞAHİN) okuyordu. Müşterinin
  "başkasının satırında hesaplama yapıyor" dediği tam olarak bu.
  - `excel_adapter._formulleri_kaydir()` — kayan her satırın formülü, hücrenin kaymadan
    önceki konumundan bugünkü konumuna `Translator` ile çevrilir. Hem silmede (−1) hem
    eklemede (+1) çalışır.
  - TOPLAM satırı bilinçli olarak bu çevirinin DIŞINDA: `=SUM(E3:E55)` çevrilseydi aralığın
    başı da kayardı (`=SUM(E4:E56)`). Onun yalnızca bitişi `_toplam_araliklarini_genislet/
    daralt` ile düzeltilir.
- **Bozulan müşteri dosyası kurtarıldı.** Master, ilk yükleme yedeğinden (3 Temmuz,
  formülleri sağlam) geri alınıp Temmuz ve Ağustos sayfaları düzeltilmiş kodla yeniden
  üretildi. Ağustos'ta doğrulama: 50 roster satırının **hiçbiri** kendi satırı dışına
  referans vermiyor.

### Doğrulama

- `pytest` 50/50 yeşil. Üç yeni test, "bir roster satırındaki hiçbir formül kendi satırı
  dışına referans veremez" değişmezini doğruluyor — silme sonrası, ekleme sonrası ve
  gerçek export sırasıyla (önce silme, sonra ekleme) birlikte.
- Testlerin hatayı gerçekten yakaladığı, düzeltme geçici olarak kapatılıp doğrulandı
  (2 test kırmızıya döndü, 49 satır hizasız çıktı).

## [4.9.2] — 2026-08-25 (yarım gün izin)

Müşteri geri bildirimi: *"yarım gün izin verirken 3 deseler az, 4 deseler fazla oluyor."*
Günlük çalışma 7,5 saat olduğu için yarım gün 3,75 saattir; sağ tık menüsünde elle yazmak
zahmetli ve yuvarlama hatasına açıktı.

### Eklenenler

- **Sağ tık menüsüne "Yarım gün" butonu.** İzin saatini tek tıkla yarım güne ayarlar ve o
  değer girilmişse butonu dolu gösterir. Altındaki satır karşılığını yazar
  ("Yarım gün = 3,75 saat (günlük 7,5 saat)").
- Değer **sabit 3,75 DEĞİL**, personelin Çalışma Tipi'ndeki `gunluk_saat`'in yarısı
  (`utils/saat.ts::yarimGunSaati`) — 8 saatlik bir tip tanımlanırsa yarım gün kendiliğinden
  4 saat olur, kod değişmez.
- İzin ve FM alanlarının adımı 0,5'ten **0,25'e** indirildi; 3,75 önceden HTML doğrulamasına
  takılan bir ara değerdi.
- Grid hücresinde yarım gün **"½"** olarak görünür — 34 piksellik hücreye "3,75i" sığmıyordu.
  Diğer saat değerleri de artık Türkçe ondalık ayırıcıyla ("3,5i"), hücrenin üzerine gelince
  tam metin çıkıyor ("3,75 saat izin").

### Hesaba etkisi

Yok — `izin_saat` zaten ondalık (`float`) taşıyordu, backend'de tek satır değişmedi. 7,5
saatlik günde 3,75 saat izin, İZİN.TL üzerinden tam olarak yarım günlük ücret keser; Ç.GÜN'e
dokunmaz. Bu davranış artık testle sabitlendi.

### Doğrulama

- `pytest` 47/47 yeşil (yeni test: 30.000 ₺ / 30 N.G'de yarım gün izin, gün maaşının tam
  yarısını keser — Ç.GÜN 30 kalır, hakediş 29.500 ₺).

## [4.9.1] — 2026-08-25 (Ç.GÜN ay bitmeden tam ay yazıyordu; ayrılmış personel sayfada duruyordu)

Müşteri geri bildirimi (aynı gün, 4.9.0'dan sonra): *"sarı olan sütun rast gele dolmuş"*,
*"daha ay bitmeden 31 gün yazıyor mesela"*. Sarı sütun Ç.GÜN. İki ayrı kural üst üste
biniyordu ve dışarıdan rastgele görünüyordu.

### Düzeltilenler

- **Ç.GÜN, içinde bulunulan ayda ayın tamamını gösteriyordu.** Hesap
  `Ç.GÜN = N.G − işe_dışı_gün − devamsız − raporlu_düşen` idi; "kaç gün geçti" diye bir
  kavram yoktu. 25 Ağustos'ta alınan çıktıda hiçbir devamsızlığı olmayan herkes 31 gün
  çalışmış görünüyordu. Değerler aslında rastgele değildi (BÜŞRA ÇETİNKAY 31−11 raporlu=20,
  HURİYE AKSU 31−6=25, DEMET ÖZTÜRK 31−3=28 — formülle birebir), ama ay bitmemişken
  "31" yazması müşteri için anlamsızdı.
  - `personel_filtre.gelecek_gun_sayisi()` — dönemin henüz gelmemiş gün sayısı;
    `hesapla()`'ya yeni `gelecek_gun` parametresi olarak geçer. **Geçmiş aylarda 0 döner,
    yani kapanmış bordrolar bit-bire-bit aynı kalır.**
  - `ise_disi_gun_sayisi` ile ÇAKIŞMAZ: yalnızca hem gelecekte hem de kişinin çalışma
    penceresi içinde olan günler sayılır. 10 Ağustos'ta çıkan biri için ayın 25'inde
    Ç.GÜN yine 10 çıkar (çift kesinti olsaydı 4 çıkardı).
  - Sunucu UTC çalıştığı için "bugün" `date.today()` ile değil sabit UTC+3 ile bulunur
    (Türkiye'de yaz saati yok); aksi halde gece 00:00-03:00 arası bir gün geri kayardı.
  - Grid özeti (`ozet()`) de aynı parametreyi kullanıyor — ekran ile Excel çelişmez.
  - ⚠️ **Bilinçli kabul edilen risk (kullanıcı kararı):** bordro ay bitmeden
    çalıştırılıyorsa Ç.GÜN eksik olacağı için maaş da eksik hesaplanır. Ayın tamamı
    isteniyorsa çıktı ay kapandıktan sonra alınmalıdır.
- **Dönem başlamadan önce işten ayrılmış personel sayfada duruyordu.** Girişleri olmadığı
  için Ç.GÜN'leri boş kalıyor, sütunun "yarısı dolu yarısı boş" görünmesinin bir sebebi de
  bu oluyordu — Ağustos sayfasında 5 kişi (ŞÜKRİYE TOZĞUN 03.06, ÖZLEM YERLİKAYA 15.06,
  HATİCE ARSLAN 22.06, FEYZİ ERKAN 13.07, AYŞE KIŞKIR 26.07). `roster_satirlarini_sil()`
  bunları o ayın sayfasından çıkarır ve TOPLAM aralıklarını daraltır. Ay İÇİNDE ayrılan
  personel silinmez — 2026-07-04 kararı gereği çıktığı ayın sonuna kadar listede kalır.
- **Gelecek tarihli girişler çift düşülüyordu.** Kullanıcılar ileriye dönük de işaretleme
  yapıyor (ör. ZÜBEYDE KURAN'ın 26-31 Ağustos raporlu günleri, BÜŞRA ÇETİNKAY'ın 26-27'si).
  Bu günler hem `gelecek_gun` içinde hem de raporlu/devamsız olarak sayılıyor, yani İKİ KEZ
  düşülüyordu — BÜŞRA'nın Ç.GÜN'ü 14 çıkıyordu, doğrusu 16. `personel_filtre.sayilan_girisler()`
  bugünden sonraki girişleri eler; "bugüne kadar" çıktısı bugüne kadarki girişlerle hesaplanır
  (henüz yaşanmamış bir fazla mesai de ödenmez). Geçmiş aylarda hiçbir giriş elenmez.
- **Export uyarısı genişletildi:** hangi ayın tamamlanmadığı (ör. "AĞUSTOS 2026 (25/31 gün)")
  ve kimlerin sayfadan çıkarıldığı `X-Puantaj-Uyari` başlığıyla arayüzde gösteriliyor.

### Bilinçli olarak DEĞİŞMEYEN

- **Puantaj girişi olmayan personelin satırı boş kalmaya devam ediyor** (kullanıcı kararı,
  2026-08-25). Ayı tam çalışan biri (hiç istisna girilmemiş) Ç.GÜN'ü boş görünür;
  CLAUDE.md §7'deki "dokunulmamış satıra yazma" kuralı korundu.

### Doğrulama

- `pytest` 46/46 yeşil (13 yeni test: geçmiş ayda gelecek_gun=0, ay ortası kalan gün,
  ay içinde ayrılanda çift kesinti olmaması, ay ortasında başlayan, Ç.GÜN'ün negatife
  düşmemesi, TOPLAM aralığının silmede daralması, gelecek tarihli girişlerin elenmesi).

## [4.9.0] — Faz 4.9 — 2026-08-25 (kritik: export yanlış sekmede açılıyor + sessiz veri kaybı + 6 haftalık log körlüğü)

Müşteri bildirimi: *"normal puantajları giriyoruz, bazen personel de ekliyoruz, ama Excel
çıktısı aldığımızda güncel girdiğimiz tabloyu değil bambaşka bir şeyi çıktı alıyor."*
Canlı tenant DB'si ve müşterinin gerçek master dosyasıyla `/api/excel/export` yeniden
çalıştırılarak üç ayrı hata doğrulandı.

### Düzeltilenler

- **Export dosyası yanlış sekmede açılıyordu (ASIL ŞİKÂYET).** `copy_worksheet` yeni ay
  sayfasını workbook'un EN SONUNA — "ÇALIŞAN LİSTESİ"/"servis" yardımcı sekmelerinden de
  sonraya — ekliyordu; workbook'un aktif sekmesi ise master'dan miras kalan
  `HAZİRAN 2026 ELDEN` idi. Kullanıcı Ağustos'u export edip dosyayı açtığında karşısına
  Haziran'ın elden ödeme tablosu geliyor, doğru yazılmış AĞUSTOS sekmesi 17 sekmenin en
  sağında ekran dışında kalıyordu. **Veri her zaman doğruydu, yanlış olan açılış sekmesiydi.**
  - `excel_adapter.sayfayi_kronolojik_yerlestir()` — yeni ay kendi kronolojik yerine taşınır
    (Ağustos artık `HAZİRAN 2026 ELDEN`'den sonra, `ÇALIŞAN LİSTESİ`'nden önce).
  - `excel_adapter.aktif_sayfa_yap()` — dosya, yazılan en güncel ayın sekmesinde açılır;
    diğer sekmelerin `tabSelected` bayrağı temizlenir.
- **Uygulamadan eklenen personelin puantajı sessizce kayboluyordu.** Roster Excel master'dan
  okunuyor, master ise 3 Temmuz'daki ilk yüklemede donmuştu (en güncel sayfası HAZİRAN, 53
  kişi); DB'de ise 66 personel vardı. Roster'da satırı olmayan kişi `continue` ile atlanıyordu —
  ne hata ne uyarı. Ağustos 2026'da RÜMEYSA TEMURAYAK'ın tüm girişleri bu şekilde düşmüştü,
  24 Ağustos'ta eklenen SELDA ÇÖKMÜŞ de aynı akıbete gidiyordu.
  - `excel_adapter.roster_satiri_ekle()` — TOPLAM'ın üstüne satır açar; stil ve satır
    formülleri (Y.TL, HAKEDİŞ, TOPLAM zinciri) son roster satırından `Translator` ile
    çevrilerek kopyalanır. `openpyxl.insert_rows` formülleri kaydırmadığı için TOPLAM
    satırındaki `=SUM(E3:E55)` aralıkları da yeni satırı kapsayacak şekilde genişletilir.
  - Export yanıtına `X-Puantaj-Uyari` başlığı eklendi; grid ve ayarlar ekranları kimler için
    satır açıldığını (veya açılamadığını) kullanıcıya gösterir.
- **Export kümülatif değildi.** Üretilen yeni ay sayfaları yalnızca indirilen dosyaya
  konuyor, master'a hiç yazılmıyordu; her export Haziran'dan sıfırdan türetildiği için
  müşterinin dosyada yaptığı manuel girdiler (avans/icra/prim/BES) ve personel değişiklikleri
  her seferinde kayboluyordu. Artık workbook master'ın üzerine atomik olarak yazılır
  (`_master_kaydet`), ilk üzerine yazmadan önce `*_master.ilk_yukleme.xlsx` yedeği alınır.
  - Kalıcılığın iki yan etkisi kapatıldı: (1) hiç puantaj girişi olmayan dönemde uygulama
    kaynak sayılmaz, master'daki tarihî sayfaya (müşterinin Ocak-Haziran verisi) hiç
    dokunulmaz; (2) girişi kaldırılan kişinin önceki export'tan kalan değeri asılı kalmasın
    diye dokunulmamış roster satırları da yazma alanları için sıfırlanır — sayfa her export'ta
    sıfırdan üretiliyormuş gibi deterministik kalır.
  - `en_guncel_sheet(..., once=)` — bir ayın şablonu kendinden SONRAKİ bir ay olamaz. Master
    kalıcı olduğu için Ağustos dosyada varken Temmuz export edilirse şablon Ağustos olur,
    Ağustos'ta işe girmiş personel Temmuz roster'ında belirirdi.
- **Dönem sırası deterministik değildi.** `disa_aktar`'daki dönem sorgusunda `ORDER BY` yoktu;
  yeni ay sayfası "o an workbook'ta bulunan en güncel sayfa"dan kopyalandığı için Ağustos'un
  şablonunun Temmuz mu Haziran mı olacağı DB'nin döndürdüğü sıraya kalmıştı.
  `ORDER BY yil, ay` eklendi.
- **Uygulama 6 haftadır tek satır log üretmiyordu.** `alembic/env.py`'deki
  `fileConfig(config.config_file_name)` çağrısı `disable_existing_loggers=True` varsayılanıyla
  çalışıyor; `core/tenant_db.py` migration'ları CANLI FastAPI process'inin içinde
  (`command.upgrade`) çalıştırdığı için ilk tenant girişinde (2026-07-09 14:50) `uvicorn.access`,
  `uvicorn.error` ve tüm `operon_puantaj.*` logger'ları kalıcı olarak susmuştu. Müşteri hata
  bildirdiğinde elde hiçbir kayıt yoktu.
  - `disable_existing_loggers=False` + Dockerfile'a `PYTHONUNBUFFERED=1`.
  - `core/logging_setup.py` — uygulama logger'ı kendi handler'ını taşır ve root'a yayılmaz;
    `fileConfig`'in root'u yeniden kurması artık onu etkilemez.
  - `main.py`'ye kendi erişim logu middleware'i (uvicorn'un access logger'ına bağımlı değil).
- **Tanımsız `/api/*` yolları 200 + HTML dönüyordu.** SPA catch-all'a düşüyorlardı; frontend
  JSON beklerken HTML alıyor, hata "anlamsız ekran" olarak yansıyor ve sunucuda iz kalmıyordu.
  Artık dürüst 404 JSON döner. `/api/health` de gerçek bir uç nokta oldu — Traefik'in sağlık
  kontrolü uygulama tamamen bozukken bile yeşil kalıyordu.

### Eklenenler

- **Sürüm bilgisi ve "eski paket" uyarısı.** `GET /api/surum` (kimlik doğrulaması istemez)
  canlıdaki sürümü döndürür; `/health` ve `/api/health` yanıtlarına da eklendi. Arayüzde
  başlığın yanında sürüm rozeti var. Rozet, arayüze gömülü sürümü sunucununkiyle
  karşılaştırır: kullanıcının tarayıcısında önbellekten eski bir paket açıksa düzeltilmiş bir
  hatayı görmeye devam eder ve bunu anlamasının hiçbir yolu yoktur — bu durumda rozet
  "yenileyin" uyarısına döner (bugün müşteriye Ctrl+F5 dedirtmek zorunda kalmamızın nedeni).
- **`error_log` tablosu + global exception handler.** Yakalanmamış her hata tenant DB'sine
  traceback'iyle yazılır, kullanıcıya `E-xxxxxxxx` takip kodu gösterilir. Güvenlik ekranına
  "Sunucu Hataları" sekmesi eklendi (`GET /api/hatalar`, `audit_gorebilir` izniyle) —
  müşteri kodu söylediğinde kayıt tek hamlede bulunur. DB yazımı best-effort'tur; hata
  yolunda ikinci bir istisna üretilmez.

- **`models/__init__.py` `PersonelMaasGecmisi`'yi kaydetmiyordu.** Dosyanın kendi
  docstring'i "Alembic autogenerate için şart" diyor; model burada kayıtlı olmadığı için bir
  `alembic revision --autogenerate` çalıştırması `personel_maas_gecmisi` tablosunu fazlalık
  sayıp **DROP** önerirdi — maaş tarihçesinin tamamı. Henüz tetiklenmemiş bir mayındı.

### Doğrulama

- `pytest` 33/33 yeşil (4 yeni regresyon testi: kronolojik yerleştirme, aktif sekme,
  roster satırı ekleme, TOPLAM aralığı genişletme — hepsi gerçek BESIM.xlsx üzerinde).
- Canlı sunucuda uçtan uca: Ağustos export'u `AĞUSTOS 2026 BANKA` sekmesinde açılıyor,
  RÜMEYSA TEMURAYAK (satır 56) ve SELDA ÇÖKMÜŞ (satır 57) hesaplanmış değerleriyle yerinde,
  `TOPLAM` 58. satırda `=SUM(E3:E57)`. İkinci export idempotent (mükerrer satır yok).
  Tüm dönemler export'unda Temmuz Haziran'dan türetildi, Ağustos'tan değil.
  Haziran BANKA ve ELDEN sayfaları ilk yüklemeyle **bit-bire-bit aynı** (0 fark).
- 500 yanıtı `{"detail": "...", "istek_id": "E-xxxxxxxx"}` döndürüyor, kayıt DB'de okunabiliyor.

## [Faz 4.8] — 2026-07-06 (kritik: maaş zammı geçmiş bordroyu bozuyordu)

### Eklenenler

- **Maaş geçmişi (etkin-tarihli zam mekanizması)** — kullanıcı sorusu: "yıllar boyunca
  sorunsuz çalışması için düşünmeliyiz... maaşlara zam gelince onu sisteme nasıl alacağız?"
  Kod taraması gerçek bir açık ortaya çıkardı: `Personel.maas` tek bir "güncel" değerdi, hiç
  geçmiş tutmuyordu — hem grid özeti (`ozet()`) hem Excel export, hangi GEÇMİŞ dönem
  hesaplanıyor olursa olsun her zaman BUGÜNKÜ maaşı okuyordu. Birine zam yapılınca geçmiş
  ayların bordrosu da (görünüşte) sessizce yeni maaşla yeniden hesaplanıyordu — N.G için
  Faz 4'te çözülen sorunun birebir aynısı, ama maaş hiç ele alınmamıştı.
  - Yeni tablo `PersonelMaasGecmisi` (personel_id, yil, ay, maas) — **etkin-tarihli/carry-forward**
    semantiği: bir kayıt, girildiği (yıl,ay)'dan itibaren bir SONRAKİ kayda kadar geçerli
    (N.G'nin `PersonelDonemAyar`'ından farklı — o SADECE o dönem için bir istisnaydı).
  - `personel_filtre.efektif_maas(session, personel_id, donem)` — hedef dönemden önceki/o
    döneme ait en son kaydı bulur; hiç kayıt yoksa `Personel.maas`'a düşer.
  - `POST /api/personel/{id}/zam` — ilk kez zam giriliyorsa, o ana kadarki maaşı geçmiş
    dönemler için sabitleyen bir "taban" kayıt da otomatik ekler (işe giriş tarihine, yoksa
    2000-01'e anchor'lanır) — aksi halde geçmiş dönemler de yanlışlıkla yeni maaşı görürdü.
    Aynı (yıl,ay) için tekrar girilirse üzerine yazar (düzeltme), append-only ama duplicate yok.
  - `PersonelUpdate`'ten `maas` alanı BİLİNÇLİ OLARAK kaldırıldı — artık TÜM maaş değişiklikleri
    `/zam` üzerinden, etkin dönem belirtilerek yapılmak zorunda.
  - `ozet()` ve `excel.py::disa_aktar()` artık `personel.maas` yerine `efektif_maas()` kullanıyor.
  - **Yan bulgu, aynı sınıf hata:** Excel export'ta MAAŞ kolonu da (N.G'deki gibi) müşterinin
    kendi formülleri için roster'da referans — zam girilince bu kolon da güncellenmezse
    müşterinin kendi hesapları eski maaşla yanlış sonuç üretmeye devam ederdi. N.G'nin
    `ng_kolon` yazma mantığına birebir aynı desenle `maas_kolon` yazma mantığı eklendi.
  - Frontend: `EmployeesPage.tsx`'te maaş artık salt-okunur; "Zam Gir" (etkin ay/yıl + yeni
    maaş) ve "Geçmiş" (maaş tarihçesi) butonları eklendi.
  Canlı API'de uçtan uca doğrulandı: geçmiş dönem (Haziran, izin_tl=800) zam sonrası
  DEĞİŞMEDİ; yeni dönem (Ağustos) doğru şekilde yeni maaşı kullandı (izin_tl 800→967,74,
  oran tam maaş artışıyla uyumlu); aynı ayı tekrar girme düzeltme olarak çalıştı, duplicate
  oluşmadı; audit log'a "zam" aksiyonuyla kaydedildi. Tarayıcıda uçtan uca doğrulandı, sıfır
  konsol hatası. `pytest` 29/29 yeşil (DB'ye bağımlı yeni kod, mevcut codebase pattern'i
  gereği pytest yerine canlı API ile doğrulandı — `test_excel_adapter.py`/Faz 3-4 aynı yöntemi kullanıyor).

## [Faz 4.7] — 2026-07-06 (yıl geçişi riski — kullanıcı sorusu üzerine bulundu)

### Eklenenler

- **Yıl geçişi (ör. 2026→2027) resmi tatil uyarısı** — kullanıcı sorusu: "bu yıl bitince 2027'ye
  geçince ne olacak?" Kod taraması: dönem seçici, N.G hesabı ve Excel sheet ayrıştırma/oluşturma
  tamamen dinamik (yıl hardcode değil) — sorunsuz. TEK gerçek risk: resmi tatiller
  (`VARSAYILAN_TATIL_2026`, `alembic/versions/81f9c9647f37_seed_data.py`) kuruluşta BİR KEZ
  seed ediliyor; özellikle dini bayramlar (Ramazan/Kurban) her yıl kaydığı için otomatik
  hesaplanamaz — biri Tatiller ekranından elle girmezse, yeni yılın resmi tatilinde çalışılan FM
  sessizce hafta içi oranıyla hesaplanır. Çözüm: `AttendanceGridPage.tsx`'e, seçilen dönemin
  yılında hiç tatil kaydı yoksa `tatil_yonetebilir` iznine sahip kullanıcılara bir uyarı
  banner'ı eklendi ("Tatilleri Gir" butonuyla doğrudan Tatiller dialogunu açıyor). Gerçek 2027
  dönemi oluşturulup tarayıcıda doğrulandı (uyarı çıktı, buton dialogu doğru açtı), sonra test
  verisi temizlendi. `pytest` 29/29 yeşil.

## [Faz 4.6] — 2026-07-06 (Emine geri bildirimi — şifre değiştirme ve Güvenlik sayfası kafa karışıklığı)

### Eklenenler

- **Kendi şifresini değiştirme** — kullanıcı geri bildirimi: "Portal'dan üretilen şifre çok
  karmaşık ve kendi şifremi nereden değiştireceğimi göremiyorum." Backend zaten kendi şifresini
  değiştirmeye izin veriyordu (`POST /api/kullanicilar/{id}/parola-degistir`, `KULLANICI_YONETEBILIR`
  izni yalnızca BAŞKASININ şifresini değiştirirken gerekiyordu) — sadece frontend UI'ı yoktu.
  `AppLayout.tsx`'e, tüm rollere (Admin/Kullanıcı/GM fark etmeksizin) her sayfada görünen bir
  "Şifremi Değiştir" butonu + dialog eklendi (yeni şifre + tekrar doğrulama, en az 6 karakter,
  eşleşme kontrolü). Ayrı bir izin gerektirmiyor, `kullanici_yonetebilir` sayfasına (Kullanıcılar)
  gitmeye gerek yok.
- **Sayfa başına açıklama metni** — kullanıcı geri bildirimi: "Güvenlik sayfası adı itibarıyla
  yanlış mesaj veriyor, kullanıcılar işlevini anlamıyor." Personel/Çalışma Tipleri/Kullanıcılar/
  Excel Aktarım/Şirket Ayarları/Güvenlik sayfalarının hepsine başlığın altına kısa bir açıklama
  eklendi. Güvenlik sayfasınınki özellikle netleştiriyor: "Bu bir hesap/şifre ayarı sayfası
  DEĞİLDİR... Kendi şifrenizi değiştirmek için sağ üstteki 'Şifremi Değiştir' butonunu kullanın."
  (Puantaj/grid ekranına bilinçli olarak dokunulmadı — zaten önceden dikey alan sorunu yaşanmış
  en yoğun kullanılan ekran, gereksiz yükseklik eklenmedi.)

### Düzeltilenler

- **Yan bulgu, bu işle ilgisiz:** backend süreci, diskteki `CalismaTipi` modelindeki
  `resmi_tatil_fm_orani`/`hafta_tatili_gunleri` alanlarını (Faz 3'te eklenmiş) yansıtmayan ESKİ
  bir kodla çalışıyordu — `/api/calisma-tipleri` bu alanları hiç dönmüyordu, bu da Çalışma
  Tipleri sayfasında `t.hafta_tatili_gunleri.includes(...)` çağrısında `undefined` hatasıyla
  komple sayfa çökmesine yol açıyordu. Backend'in temiz yeniden başlatılmasıyla düzeltildi
  (klasik "uvicorn --reload eski kodu sunmaya devam ediyor" durumu).

## [Faz 4.5] — 2026-07-06 (dördüncü tur — N.G kolonu güncellenmiyordu)

### Düzeltilenler

- **Excel export'ta N.G kolonu hep önceki ayın statik değerini gösteriyordu**
  (ör. Temmuz'a kopyalanan roster'da hep Haziran'ın 30'u) — kullanıcı geri
  bildirimi: "Ç.G 31 olanları alamıyor, sanırım N.G 30 olduğu için". Bizim
  hesabımız (E/Ç.GÜN vb.) doğru N.G'yi (`efektif_ng`) kullanıyordu ama
  müşterinin KENDİ Excel formülleri (Y.TL=MAAŞ/N.G gibi) roster'daki eski N.G
  hücresini okuyup yanlış hesaplıyordu — bizim rakamlarımızla müşterinin kendi
  formül çıktıları arasında sessiz bir tutarsızlık oluşuyordu.
  Düzeltme: `disa_aktar` artık her dönem için TÜM roster satırlarında (dokunulmuş
  olsun olmasın) N.G hücresini o kişinin o ay için efektif değeriyle güncelliyor.
  Yerel dev DB'deki gerçek Temmuz verisiyle uçtan uca doğrulandı — N.G tüm
  satırlarda 30'dan 31'e güncellendi, formüller doğru hücreye referans veriyor.

## [Faz 4.4] — 2026-07-06 (Faz 4.3'ün düzeltmesi — aynı gün, üçüncü tur)

### Düzeltilenler

- **Faz 4.3, mapping'in bilmediği HER kolonu (formül olsa bile) temizliyordu** —
  kullanıcı geri bildirimi: "tüm formülleri sildin haziran'dan". Y.TL/MAAŞ(hesaplanan)/
  M.1/M.1.5/İZİN.TL/HAKEDİŞ/TOPLAM gibi kolonlar mapping'te tanımlı değil ama FORMÜL
  (aynı satırdaki hücrelerden otomatik hesaplanan yapı) — bunlar "önceki ayın manuel
  girdisi" değil, temizlenince tüm hesap zinciri kopuyordu.
  Düzeltme: artık kural "kolon mapping'te mi" değil "hücre FORMÜL mü" — formül olan
  HER hücre (hangi kolonda olursa olsun) korunuyor; yalnızca formül OLMAYAN düz
  değerler (AVANS gibi gerçek manuel girdiler) mapping dışı kolonlarda temizleniyor.
  Gerçek dosyayla (Emine'nin güncel production dosyası) 10 rastgele Temmuz kaydıyla
  tekrar uçtan uca doğrulandı — bu kez tüm formül kolonları (F/G/H/I/M/O/R) hem
  dokunulan hem dokunulmayan satırlarda sağlam, başlık hücresinin gerçek konumu
  (B1, birleştirilmiş B1:U1) bulunup doğru güncellendi, Haziran sayfası bozulmadı.

## [Faz 4.3] — 2026-07-06 (Faz 4.2'nin düzeltmesi — aynı gün)

### Düzeltilenler

- **Faz 4.2'nin ilk sürümü referans (Haziran) sayfayı OLDUĞU GİBİ kopyalıyordu** —
  kullanıcı geri bildirimi: "o avans çıkışları filan hazirana ait, başlık da hâlâ
  haziran". `yeni_ay_sayfasi_olustur` artık: (1) mapping'in bilmediği kolonları
  (AVANS/İCRA/BES/PRİM/TOPLAM/ETA/FARK gibi — önceki ayın kendine özgü manuel
  girdileri) roster satırlarında temizliyor, (2) `yazma_alanlari`'nı (Ç.GÜN/İZİN/FM)
  da temizliyor (dokunulmamış satırda eski ayın FM'i yanlışlıkla yeni aya taşınmasın
  diye), (3) sayfadaki "HAZİRAN 2026" gibi eski ay/yıl metnini "TEMMUZ 2026" ile
  değiştiriyor (metin ara/değiştir — başlık hücresinin konumu mapping'te bilinmiyor).
  **Gerçek dosyayla, gerçek 10 rastgele Temmuz kaydıyla uçtan uca doğrulandı** —
  çıktı dosyası hücre hücre kontrol edildi: roster/hesaplanan değerler doğru,
  AVANS temizlenmiş, başlık güncel, dokunulmamış satırlar boş, Haziran sayfası
  hiç bozulmamış. Otomatik regresyon testi de bu davranışı doğruluyor.

## [Faz 4.2] — 2026-07-06 (kritik: yeni ay export'ta hiç görünmüyordu)

### Düzeltilenler

- **Excel export'ta güncel ay hiç görünmüyordu** — kullanıcı geri bildirimi: "Temmuz
  kısmı doldu ama Temmuz sheeti bile yok!!!". Kök neden: `disa_aktar`, bir dönemin
  Excel'de eşleşen bir sayfası yoksa o dönemi SESSİZCE atlıyordu — Emine'nin gerçek
  dosyası yalnızca Ocak-Haziran içeriyordu, Temmuz için (yeni/güncel ay) hiç sayfa
  yoktu, dolayısıyla grid'de günlerce girilen 20 Temmuz kaydı export dosyasında hiç
  görünmüyordu.
  Düzeltme: `excel_adapter.py`'ye `en_guncel_sheet` (şablon için en son mevcut ayı
  bulur) ve `yeni_ay_sayfasi_olustur` (openpyxl `copy_worksheet` ile roster/format/
  formüller dahil kopyalar, yeniden adlandırır) eklendi; `disa_aktar` artık eşleşen
  sayfa yoksa bunu otomatik oluşturuyor. Emine'nin tenant'ındaki bozuk
  `excel_sheet_adi` referansı ("TEMMUZ 2026 BANKA (2)" — dosyada hiç yoktu) kendiliğinden
  düzeliyor, elle veri müdahalesi gerekmedi. Emine'nin GERÇEK dosyasıyla uçtan uca
  yerel olarak doğrulandı + kalıcı regresyon testi eklendi (`test_excel_adapter.py`).

## [Faz 4.1] — 2026-07-06 (kritik depolama düzeltmesi)

### Güvenlik / Veri Kalıcılığı

- **Yüklenen Excel dosyaları kalıcı DEĞİLDİ** — `docker-compose.yml`'de `data/uploads`
  için kalıcı bir volume yoktu ve `.dockerignore` bu dizini build context'ten
  hariç tutmuyordu. Sonuç: HER `docker compose build puantaj` deploy'unda, container'ın
  yüklü Excel dosyaları local repo'daki demo `1_master.xlsx` ile SESSİZCE eziliyordu —
  Faz 4 deploy'u sonrası Emine'nin "Excel'e Aktar" özelliği bu yüzden 404 vermeye
  başladı (`_master_dosya_yolu`'nun Faz 4'te tenant-scoped hale gelmesiyle birleşince,
  dosya hiç var olmayan bir yolda aranıyordu). Düzeltildi: `puantaj_uploads` adında
  kalıcı bir Docker volume eklendi, `.dockerignore`'a `backend/app/data/uploads`
  eklendi (artık image'a hiç gömülmüyor). Emine'nin mevcut dosyası container'dan
  yedeklenip yeni kalıcı volume'e doğru tenant-scoped yola (`emine_1_master.xlsx`)
  geri kondu — veri kaybı olmadı.

## [Faz 4] — 2026-07-06

### Eklenenler

**N.G artık dönem bazlı, kişi bazlı istisna edilebilir** (kullanıcı geri bildirimi: "kişi
bazında Ç.G değişmiyor, ay ay komple değişebiliyor ama aynı ay içinde biri 30 biri 31
olmuyor" — önceden `Personel.ng` kişi bazında sabitti, ay değişse bile güncellenmiyordu):
- `Donem.ng` (yeni alan) — dönem oluşturulunca OTOMATİK olarak ayın takvim gün sayısına
  eşitlenir (Ocak/Mart/Mayıs/Temmuz/Ağustos→31, Nisan/Haziran→30, Şubat→28/29).
- `PersonelDonemAyar` (yeni tablo) — kişi bazlı istisna, SADECE ilgili dönem için;
  `PUT /api/puantaj/{personel_id}/donem/{donem_id}/ng` (`ng: null` = istisnayı kaldır).
- Grid'de personel adı hücresindeki N.G artık düzenlenebilir (kalem ikonu,
  `personel_yonetebilir` izni gerektirir) — o dönem için anlık istisna girilebilir.
- `PersonelOzet.ng` — o dönem için EFEKTİF N.G'yi (istisna veya takvim varsayılanı) döner.

**Excel export'ta gözden kaçan 3-tier FM tutarsızlığı düzeltildi** — `excel.py::disa_aktar`
Faz 3'te `resmi_tatil_fm_orani`/`hafta_tatili_gunleri` parametrelerini hiç almıyordu (yalnızca
grid'in `ozet` endpoint'i güncellenmişti); artık ikisi de aynı 3-kademeli hesabı kullanıyor.

### Güvenlik

- **Tenant'lar arası Excel dosya çakışması bulundu ve düzeltildi** — `data/uploads/
  {sirket_id}_master.xlsx` yalnızca sirket_id'ye göre isimlendiriliyordu; her tenant'ın kendi
  izole DB'sinde Sirket id'si HER ZAMAN 1'den başladığı için, farklı tenant'lar (ör. "emine" ve
  "platform_admin") aynı fiziksel dosyayı paylaşıp birbirinin Excel içeriğini sessizce
  eziyordu. `core/tenant_scope.py` (yeni) tenant_slug'ı (SaaS modda) veya sabit bir anahtarı
  (onprem modda) yola katan bir önek üretir; `_master_dosya_yolu` artık `{tenant}_{sirket_id}_
  master.xlsx` kullanıyor.

### Düzeltilenler

- **Excel import artık personel roster'ını yalnızca EN GÜNCEL eşleşen sayfadan alıyor**
  (`excel.py::ice_aktar`) — önceden dosyadaki TÜM aylık "BANKA" sayfaları işleniyor, her ayda
  görülen her isim kalıcı personel olarak ekleniyordu. Gerçek örnek: 6 aylık (Ocak-Haziran)
  bir dosyada personel devri normal olduğu için 64 farklı isim birikmişti, oysa güncel (Haziran)
  kadro sadece 53 kişiydi — ayrılmış kişiler "aktif" görünüyordu. Artık yalnızca en güncel
  sayfanın kadrosu roster olarak alınır; diğer sayfalar hâlâ Dönem kaydı için taranır (dönem
  seçicide görünsünler diye) ama personel oluşturmaz/güncellemez.
- Emine'nin tenant'ında (`tenant_emine_puantaj`) bu buggy import'tan kalan 11 fantom personel
  elle "ayrıldı" (`isten_cikis_tarihi=2026-06-30`) olarak işaretlendi — silinmedi, ilişkili
  kayıtlar korundu.

## [Faz 3.1] — 2026-07-05 (aynı gün düzeltme)

### Düzeltilenler

- **Beyaz Yaka (5 gün) için "hafta tatili" varsayılanı YANLIŞTI** — gerçek müşteri geri
  bildirimi (Emine): 5 gün çalışan bir tipte Cumartesi sadece normal çalışılmayan gün,
  "hafta tatili" (×2 primli) DEĞİL — Cumartesi mesaisi hafta içi oranıyla (×1,5) ödenmeli.
  Tek hafta tatili günü her zaman Pazar. Faz 3'te yanlışlıkla `haftalik_gun=5` için
  varsayılan `[Cmt,Paz]` yapılmıştı; artık `haftalik_gun`'dan bağımsız her zaman yalnızca
  `[Paz]` öneriliyor (migration `51e979ff9e3e` düzeltildi, `EmployeeTypesPage.tsx`'teki
  öneri fonksiyonu düzeltildi). Üretimdeki iki tenant'ın (`platform_admin`, `emine`) BY
  satırları elle düzeltildi (`hafta_tatili_gunleri: [5,6] → [6]`).
  **Sistem tasarımı kendini kanıtladı:** Çalışma Tipi bazında hafta tatili günü ayarlanabilir
  olduğu için düzeltme sadece bir veri/varsayılan değişikliği — kod/hesap motorunda hiçbir
  değişiklik gerekmedi, şirket isterse Çalışma Tipleri sayfasından Cumartesi'yi yine
  ekleyebilir.

## [Faz 3] — 2026-07-05

### Eklenenler

**Esnek Çalışma Tipi parametreleri** (kullanıcı geri bildirimi: "Şirket ayarları bu kadar
olamaz" — FM çarpanı ve hafta tatili günü şirkete göre çok değişiyor, internet araştırmasıyla
desteklendi: İş Kanunu asgari fazla mesai %50/1,5×, resmi tatil/hafta tatili çalışması genelde
%100/2×, toplu iş sözleşmeleri bunun üzerine çıkabiliyor ve resmi tatili hafta tatilinden ayrı
oranla ele alabiliyor).
- `CalismaTipi.hafta_tatili_gunleri` (yeni) — hangi gün(ler)in bu tip için hafta tatili
  sayıldığı artık ayarlanabilir (önceden kodda HER ZAMAN Pazar sabitti, `haftalik_gun` alanı
  var olduğu halde hesap motorunda hiç kullanılmıyordu).
- `CalismaTipi.resmi_tatil_fm_orani` (yeni) — resmi tatil artık hafta tatilinden BAĞIMSIZ
  kendi FM oranına sahip (3 kademeli: hafta içi / hafta tatili / resmi tatil).
- "Çalışma Tipleri" sayfasına 7 günlük hafta tatili seçici (checkbox) + "FM Resmi Tatil" alanı
  + tek tıkla üç oranı eşitleyen **"Sabit Oran"** butonu eklendi.
- **Personel sayfasında satır içi düzenleme** — önceden yalnızca yeni personel eklenebiliyordu;
  artık mevcut bir kişinin çalışma tipi/maaş/N.G/işe giriş tarihi Excel'e dönmeden düzeltilebilir
  (kullanıcı geri bildirimi: "çalışma günü her zaman Excel'den gelmeyebilir").
- Grid'de hafta tatili vurgusu artık **kişiye göre** — 5 gün çalışan bir tipin Cumartesi hücresi
  de doğru şekilde vurgulanıyor (önceden tüm satırlar için tek tip Pazar vurgusu vardı).

### Değiştirilenler

- `payroll_calc.py::fm_orani` üç kademeye çıktı: resmi tatil → hafta tatili (kişiye özel gün) →
  hafta içi. `hesapla()` yeni `resmi_tatil_fm_orani`/`hafta_tatili_gunleri` parametrelerini alıyor.
- Grid header satırında artık yalnızca **resmi tatil** vurgusu var (herkes için aynı); hafta
  tatili vurgusu kişiye göre değiştiği için yalnızca gövde hücrelerinde gösteriliyor.

### Güvenlik / Payroll Doğruluğu — ÖNEMLİ

- **Gerçek payroll etkisi:** `haftalik_gun=5` olan bir Çalışma Tipi için hafta tatili günleri
  artık `[Cumartesi, Pazar]` (önceden yalnızca Pazar). Böyle bir tipte zaten girilmiş Cumartesi
  FM saati varsa, bu migration'dan (`51e979ff9e3e`) sonra o kişinin FM tutarı DEĞİŞİR (hafta
  tatili oranı uygulanır — genelde daha yüksek, işçi lehine). Migration'ın backfill'i mevcut
  demo veriyi (BESIM, tüm personel `MY`/6-gün tipinde) ETKİLEMEDİ — yerelde doğrulandı, FM
  tutarları migration öncesi/sonrası birebir aynı kaldı.

### Doğrulama

- `python -m pytest tests/ -q` — 28/28 geçti (11 yeni/güncellenmiş test dahil).
- Migration yerel dev DB'sinde çalıştırıldı, backfill sonuçları elle doğrulandı (BY→[5,6],
  MY→[6], `resmi_tatil_fm_orani` her ikisinde de eski `hafta_sonu_fm_orani` değeriyle aynı).
- Frontend `npm run build` (tsc dahil) hatasız.

## [Faz 2] — 2026-07-05

### Eklenenler

**SaaS Portal Entegrasyonu**
- Dual auth-mode mimari — `AUTH_MODE` env'i (`onprem` varsayılan | `saas`); `core/database.py`/
  `core/security.py`, `get_session`/`get_current_user`'ı import zamanında bu değere göre iki
  implementasyondan birine bağlıyor. Mevcut 10 route dosyası hiç değişmedi.
- `app/services/portal_sso_service.py` — Portal'ın RS256 public key'ini fetch+cache eden, JWT
  doğrulayan servis (SaaS_Platform/apps/SRM'in kanıtlanmış deseninin uyarlaması).
- `app/core/tenant_db.py` — Multi-tenant DB çözümleme: JWT'deki `tenant_slug`'a göre
  `tenant_{slug}_puantaj` DB'si lazy oluşturuluyor + programatik `alembic upgrade head`
  çalıştırılıyor (seed migration dahil, Sirket+3 Rol otomatik hazır oluyor).
- `app/core/auth_context.py` — SaaS modda paylaşılan JWT-context dependency'si (FastAPI'nin
  request-içi dependency cache'lemesi sayesinde JWT doğrulama bir istekte tek sefer çalışıyor).
- **JIT (just-in-time) kullanıcı kaydı** (`core/security.py::get_current_user_saas`) — ilk SSO
  girişinde JWT'deki `username`+`role` ile eşleşen yerel `Kullanici` yoksa otomatik oluşturuluyor,
  rol portal'da değişirse senkronize ediliyor.
- `api/routes/sso.py` — `/api/sso/login` (RS256 JWT doğrulama + `access_token` httponly cookie)
  ve `/api/sso/logout` (JS'ten silinemeyen cookie'yi backend temizliyor).
- `main.py` — statik frontend servisi (Docker imajında gömülü React build'i aynı container'dan
  sunmak için) + SPA catch-all route.
- `Dockerfile` + `docker-compose.yml` + `.dockerignore` — SRM'in kanıtlanmış deseni: kendi
  Postgres container'ı, Traefik label'ları (`puantaj.kolektif360.com`).
- Ana Puantaj (grid) sayfasına **"Excel'e Aktar" butonu** eklendi — önceden yalnızca ayrı
  Excel Aktarım sayfasında vardı.

### Değiştirilenler

- **Kullanıcılar sayfası SaaS modda tamamen gizlendi** (`App.tsx` route hiç register edilmiyor,
  `AppLayout.tsx` nav linki de kalkıyor) — rol/kullanıcı ataması SaaS'ta Portal'ın "Manage"
  ekranından yapılıyor (CLAUDE.md §8.8 kararıyla uyumlu).
- **Grid'de sağ özet kolonları (Ç.GÜN…FM ₺) artık sticky DEĞİL** — kullanıcı geri bildirimiyle
  kaldırıldı, artık gün kolonlarıyla birlikte yatay kayıyor. (Sol personel-adı kolonu ve header
  satırı hâlâ sticky — bu değişmedi.)
- Portal tarafı: `provision_puantaj.py`, `admin_apps.html` kartı, `admin/services/status_service.py`
  health-check girişi — `apps/portal`'a eklendi.

### Düzeltilenler

- `AuthContext.tsx`'te SaaS modda `getToken()` kısa devresi (localStorage kontrolü) `/me`
  çağrısını hiç yapılmaz hale getiriyordu — cookie tabanlı SaaS auth'ta localStorage boş olduğu
  için oturum asla doğrulanmıyordu. Test sırasında yakalanan gerçek bir regresyon adayıydı.

### Güvenlik

- **Path traversal (CWE-22) bulundu ve düzeltildi** — `main.py`'deki SPA catch-all route,
  `full_path` parametresini `resolve()` etmeden dosya sistemine karşı kontrol ediyordu; bu,
  `/%2e%2e/%2e%2e/...` gibi bir istekle container içindeki herhangi bir dosyanın (kaynak kodu
  dahil) okunabilmesine izin veriyordu. Deploy sonrası canlıda otomatik tarayıcı botlarının
  rutin trafiği fark edilirken keşfedildi, yerelde doğrulanıp `candidate.resolve().is_relative_to(
  _static_resolved)` kontrolüyle düzeltildi, hem yerelde hem üretimde tekrar doğrulandı.

### Kapsam Dışı Bırakılan / Ertelenen

- **Tenant erişimi otomasyonu** — `provision_puantaj.py` bilinçli olarak yalnızca `apps` tablosuna
  kayıt ekliyor; hangi tenant'a Puantaj açılacağı ve rol ataması (`tenant_app_settings.roles`)
  admin panelden elle yapılıyor, otomatikleştirilmedi.

### Deploy

- `https://puantaj.kolektif360.com` canlı — Traefik + Let's Encrypt sertifikası, gerçek Portal
  SSO akışıyla (admin panel "Aç" butonu) tarayıcıda uçtan uca doğrulandı. Demo amaçlı BESIM.xlsx
  mapping template'i (`data/seed/besim_mapping.json`) üretim tenant DB'sine eklendi.

### Yerleşim (kapandı)

- `E:\Mira\Operon_Puantaj` ile `E:\Mira\SaaS\apps\Operon_Puantaj` (iki ayrı fiziksel klasör,
  sembolik link değil) birleştirildi — `E:\Mira\SaaS\apps\Operon_Puantaj` tek asıl (canonical)
  konum kabul edildi, diğeri robocopy /MIR ile eşitlendi.

---

## [Faz 1] — 2026-07-04

### Eklenenler

**Bordro hesap motoru ve grid**
- Saf, DB'den bağımsız hesap motoru (`payroll_calc.py`): saatlik ücret, Ç.GÜN, gün maaşı,
  İZİN.TL, FM.TL, hakediş — `Puantaj.html` prototipinin `hesapla()`/`hesaplaGen()` fonksiyonlarıyla
  birebir doğrulandı.
- Takvim/grid ekranı (`PuantajGrid`/`DayCell`): sol tık devamsızlık toggle, sağ tık İzin/FM/
  Yıllık İzin/Raporlu popover'ı; sağda canlı özet kolonları (Ç.GÜN, Gün Kesintisi, Yıllık İzin,
  Raporlu, İzin s/₺, FM s/₺).
- 12 aylık dönem seçici — henüz Excel'i içe aktarılmamış aylar da "(yeni)" etiketiyle seçilebilir,
  seçildiğinde dönem sessizce (get-or-create) oluşturulur; varsayılan seçim bugünün ayı.
- Personel işe giriş/çıkış tarihleri (`ise_baslama_tarihi`/`isten_cikis_tarihi`) — eski boolean
  `aktif` alanının yerine geçti; ay bazlı görünürlük (işten çıkan o ay sonuna dek listede kalır)
  ve gün hücresi bazlı devre dışı bırakma (işe girişten önce/çıkıştan sonra tıklanamaz).
- **Kısmi ay maaşı** — ay ortasında işe giren/çıkan personelin Ç.GÜN'ü otomatik prorate edilir
  (`personel_filtre.ise_disi_gun_sayisi` → `payroll_calc.hesapla(ise_disi_gun=...)`).
- **Yıllık İzin / Raporlu tam-gün statüleri** (`gun_durumu`) — Yıllık İzin Ç.GÜN'den hiç düşmez;
  Raporlu'nun etkisi şirket politikasına bağlı (aşağıya bakın).
- **Raporlu ödeme politikası** — şirket genelinde tek ayar: Tam Öde / Hiç Ödeme (varsayılan) /
  N Gün Eşiği (ardışık her rapor bloğunun ilk N günü ödenir, kalanı düşer — "SGK devraldığı"
  varsayımı). `Sirket.raporlu_politikasi`/`raporlu_esik_gun` + `Şirket Ayarları` sayfası.
- **Çalışma Tipi bazlı FM oranları** — hafta içi/hafta sonu-tatil FM çarpanları (varsayılan
  1,5×/2×) artık her Çalışma Tipi için ayrı ayarlanabilir, Çalışma Tipleri sayfasından.
- "Gün Kesintisi" özet kolonu — devamsız/raporlu günlerin toplam ₺ maaş etkisi artık grid'de
  açıkça görünüyor (önceden hesap doğruydu ama hiçbir yerde ₺ olarak gösterilmiyordu).

**Roller, kullanıcılar, güvenlik**
- Genişletilebilir rol/izin modeli (`Rol.izinler` — serbest JSON, migrasyonsuz yeni izin
  ekleme) — seed üçlü: **Admin** (tam yetki), **Kullanıcı** (sadece puantaj girer, maaş
  görünürlüğü varsayılan gizli), **GM** (tam görünürlük + export, sıfır yazma).
- Kurulum Sihirbazı (`SetupWizardPage`) — ilk açılışta 5 adım: Şirket → Kurulum Modu (Tek/Çok
  Kullanıcı) → Admin Hesabı → [Çok Kullanıcı ise] Maaş Görünürlüğü → Özet. Kurulum
  tamamlanmadan login ekranı bile gösterilmez (`SetupGate`).
- Maaş verisi gizliliği — Tek Kullanıcı'da otomatik (kaynak Excel'de maaş var/yok), Çok
  Kullanıcı'da wizard'da Admin'in açıkça karar verdiği bir ayar (`gorebilir_maas_tutari`).
- **Kullanıcı yönetimi** — mevcut bir kullanıcının rolünü değiştirme, ad/e-posta düzenleme,
  aktif/pasif toggle, şifre sıfırlama (ayrı dialog); kendi hesabını pasife alma engellendi.
- **`/güvenlik` sayfası** — denetim kaydı (kim/ne zaman/ne değişti) admin + maaş görebilen role
  gösterilir; artık işlemi yapan kullanıcının adı da çözülüp gösteriliyor (önceden ham ID'ydi,
  hiç gösterilmiyordu). Puantaj girişi yapan ama kaydı göremeyen kullanıcılara, işlemlerin
  kayıt altında olduğunu açıkça belirten bir bilgi notu eklendi.
- Append-only denetim günlüğü (`AuditLog`) — tüm parametre değişiklikleri ve puantaj girişleri
  zaman damgalı, aktör + eski/yeni değerle kaydediliyor.

**Excel entegrasyonu**
- Mapping-tabanlı Excel adaptörü (`excel_adapter.py` + `ExcelMappingConfig`) — müşterinin Excel
  düzeni koda hiç hardcode edilmiyor; kolon/sayfa eşlemesi tamamen config'ten geliyor.
- İçe/dışa aktarım: yalnızca o dönem en az bir girişi olan personelin hücrelerine dokunulur
  (dokunulmayan personel "tam maaş aldı" anlamına gelir); FM.TL=0 iken hücreye formül (`=J*I`)
  geri yazılır, prototipin davranışı birebir korunuyor.
- **Onboarding keşif aracı** (`backend/scripts/excel_kesif.py`) — yeni bir müşteri Excel'i
  geldiğinde sheet listesini, header adaylarını, TOPLAM satırını ve ham örnek satırları
  otomatik-tahminsiz döker; mapping kararını hâlâ insan+Claude konuşması verir.

### Değiştirilenler

- Excel export ve Denetim Kaydı erişimi sertleştirildi: `excel_disa_aktarabilir` ve
  `audit_gorebilir` izinleri artık `gorebilir_maas_tutari` OLMADAN işe yaramıyor
  (`core/security.py::require_permission(*keys)` artık birden fazla izni AND ile isteyebiliyor).
  Önceden bu ikisi seed rollerde rastlantısal olarak hep birlikte geliyordu; Rol Yönetimi
  UI'ı bunları bağımsız hale getirince gerçek bir sızıntı olurdu.
- Frontend bundle code-splitting — 6 yönetim sayfası (`Personel`/`Çalışma Tipleri`/
  `Kullanıcılar`/`Excel Aktarım`/`Şirket Ayarları`/`Güvenlik`) `React.lazy()` ile ayrı
  chunk'lara bölündü; tek 535KB chunk yerine en büyük chunk 416KB'a indi.
- Denetim Kaydı sayfası `/güvenlik`'e dönüştürüldü (ayrı bir "Security Center" sayfası
  açılmadı — tekrar yok, tek nav maddesi).

### Düzeltilenler

- Grid'de eksik hücre çizgileri (`DayCell` gerçek bir MUI `TableCell` değil, ham `Box` idi).
- Pazar/resmi tatil hücrelerinin soluk rengi.
- Yatay scrollbar, düzinelerce satırın altında kalıp erişilemiyordu — grid'in `maxHeight`'ı
  sınırlandı, header sticky yapıldı.
- Grid altında fazla boş alan (`maxHeight` hesabı `calc(100vh-260px)` → `calc(100vh-192px)`).
- Personel/Çalışma Tipi/Kullanıcı listelerinde `ORDER BY` eksikti — herhangi bir düzenlemeden
  sonra satırlar görünür şekilde yer değiştiriyordu (üç endpoint'te düzeltildi).
- Üç `status_code=204` endpoint (`kullanicilar.py`/`puantaj.py`/`tatiller.py`), güncel
  FastAPI'nin (0.116) "204 body içeremez" kontrolüyle çakışıyordu — backend'in HİÇ
  başlamamasına yol açan gizli bir regresyondu; `response_model=None` eklenerek düzeltildi.
- `/api/personel` maaş alanı, önceden dar `gorebilir_maas_tutari` yerine geniş
  `puantaj_gorebilir` iznine bakıyordu — maaş her zaman dönüyordu.

### Güvenlik

- Maaş sızıntısı sertleştirmesi (yukarıda, Değiştirilenler'de detaylı).
- `/güvenlik` sayfası ve puantaj ekranındaki şeffaflık bildirimi (yukarıda, Eklenenler'de).

### Kapsam Dışı Bırakılan Kararlar (bilinçli, gerekçeli)

- **Onay iş akışı** (submit/approve/reject) — mevcut rol bazlı görünürlük yeterli kabul edildi.
- **Yıllık izin bakiyesi/hakedişi** — Puantaj bu konuyu hiç yönetmeyecek; kaynak veride bakiye
  varsa sadece kullanımını işaretler, yoksa kapsam dışı. Sabit bir "N ay çalışmadan izin yok"
  kuralı da eklenmedi (gerçek hayatta tutmuyor).
- **ETA'ya (veya başka bir bordro/muhasebe programına) doğrudan aktarım** — proaktif genel
  özellik olarak inşa edilmeyecek; gerekli altyapı (mapping mekanizması) zaten yeterli, sadece
  belirli bir müşteri isterse o müşteriye özel eklenecek.
- **Audit log hacim/arşivleme stratejisi** — `/güvenlik` özelliğiyle kapandı kabul edildi, ayrı
  bir partition/arşivleme çalışması yapılmayacak.
- **Çoklu mapping-template senaryosu** — mevcut mimari (nullable `sirket_id` FK) zaten
  destekliyor, ek kod gerekmedi.

### Mimari Araştırma (kod değil, karar/dokümantasyon)

- **SaaS Portal entegrasyonu** — Portal kaynak kodu incelenerek somut mekanizma doğrulandı:
  rol ataması Portal'da uygulama-bazında serbest metin bir liste (`tenant_app_settings.roles`);
  bu listeyi `"admin,kullanici,gm"` yaparsak Portal'ın JWT `role` claim'i bizim `Rol.kod`
  değerlerimizle birebir eşleşir, ayrı çeviri tablosu gerekmez (CLAUDE.md §8.8).
- SaaS taşıma kararı: Puantaj'ın SaaS sürümü `E:\Mira\SaaS\apps\Puantaj` altına konacak, ama
  bu Faz 1 geliştirmesi tamamen bitene kadar ertelendi.

---

## Notlar

- Bu proje git ile takip edilmiyor (henüz) — bu changelog, commit geçmişi yerine `CLAUDE.md`/
  `ROADMAP.md`'deki karar kayıtlarından derlendi.
- Tarihler, ilgili kararın `CLAUDE.md`/`ROADMAP.md`'ye işlendiği güne aittir.
