# Changelog — Operon Puantaj

> Bu dosya, `CLAUDE.md`/`ROADMAP.md`'deki karar kayıtlarının kronolojik özetidir.
> Format [Keep a Changelog](https://keepachangelog.com/) ilkelerinden esinlenir, Türkçe.
> Her girişin *neden*i için `CLAUDE.md`, açık/kapalı roadmap kalemleri için `ROADMAP.md`'ye bakın.

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
