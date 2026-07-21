# Operon Puantaj — Roadmap

> Faz 1 iskeleti tamamlandıktan sonra bilinçli olarak ertelenen kalemlerin tek listesi.
> Kapsam kararları ve gerekçeleri için `CLAUDE.md`'ye bakın. Bir kalem başlayınca buradan
> silinmez — "planned" → "in progress" → "done" olarak işaretlenip commit geçmişine referans eklenir.

## Dönem seçici (12 ay) + Personel işe giriş/çıkış tarihleri — ✅ UYGULANDI (2026-07-04)

Kullanıcı geri bildirimi: "temmuz sonuna yıllık izin girmek isteyebilir" → dönem
seçici artık mevcut dönemlerin bulunduğu yıl(lar) için 12 ayı da listeler,
henüz Excel'i içe aktarılmamış aylar "(yeni)" etiketiyle gösterilir ve
seçildiğinde `POST /api/donemler` (get-or-create) ile sessizce oluşturulur.
Varsayılan seçim: bugünün ayı dönemler arasında varsa o, yoksa en son dönem
(ileri bakmak varsayılan görünümü kaydırmasın diye).

"Giriş çıkışlar çok olur, değişiklik yapılan gün itibarı ile geçerli olmalı,
işten çıkan o ay sonuna dek listede kalmalı" → `Personel.aktif` kaldırıldı,
yerine `ise_baslama_tarihi`/`isten_cikis_tarihi` (gerçek tarihler) geldi;
`aktif` artık `isten_cikis_tarihi is None`'dan türetilen bir property.
Ay bazlı görünürlük: personel, işe giriş/çıkış tarihi o ayla kesişiyorsa
görünür (`app/services/personel_filtre.py::donemde_calisiyor_mu`, aynı
mantık frontend'de `utils/personel.ts::donemdeCalisiyorMu`) — işten çıkan
kişi çıktığı ayın sonuna kadar görünür, sonraki aydan düşer. Ay içinde de
işe girişten önceki / çıkıştan sonraki gün hücreleri devre dışı bırakılır
(`DayCell` `devreDisiMi`) ama var olan veriyi gizlemez.

## Kısmi Ay Maaşı — ✅ UYGULANDI (2026-07-04)

Ay ortasında işe giren/çıkan personelin Ç.GÜN'ü artık otomatik prorate ediliyor.
Kullanıcı kararı: "Evet, otomatik sınırla" — devre dışı bırakılan gün hücrelerine
(`DayCell.devreDisiMi`) dokunulmadan, işe-giriş-öncesi/çıkış-sonrası gün sayısı
`app/services/personel_filtre.py::ise_disi_gun_sayisi` ile hesaplanıp
`payroll_calc.hesapla(ise_disi_gun=...)`'a geçiriliyor:
`Ç.GÜN = N.G − ise_disi_gun − devamsız_gün − raporlu_düşen_gün` (min 0).
Hem `puantaj.py::ozet()` hem `excel.py::disa_aktar()` bu parametreyi geçiriyor —
grid özeti ve Excel çıktısı tutarlı. `tests/test_personel_filtre.py` (5 test) +
`test_payroll_calc.py`'deki 2 yeni testle doğrulandı, tarayıcıda regresyon yok.

## Yıllık İzin / Raporlu — ✅ UYGULANDI (2026-07-04)

Kullanıcı geri bildirimi: grid sağ-tık popover'ına Yıllık İzin / Raporlu tam-gün seçenekleri
eklendi (`PuantajGirisi.gun_durumu`: `devamsiz`/`yillik_izin`/`raporlu`), farklı renklerle
grid'de gösteriliyor (yeşil "Yi" / amber "R"), aylık özet kolonlarında sayılıyor. Bir günde ya
tam-gün statüsü ya saatlik izin/FM olur, ikisi birlikte olmaz. Uçtan uca tarayıcıda doğrulandı,
`pytest` 13/13 yeşil.

**Ödeme kuralları (kesinleşen):**
- **Yıllık İzin** → Ç.GÜN'den DÜŞMEZ, tam ödenir. Kesin kural.
- **Raporlu** → Ç.GÜN etkisi artık ŞİRKET GENELİNDE ayarlanabilir bir politika (aşağıya bakın),
  varsayılan hâlâ "Hiç Ödeme" (Devamsız gibi tam düşer) — geriye dönük uyumlu.

### Raporlu — Şirket Bazlı Ayarlanabilir Politika — ✅ UYGULANDI (2026-07-04)

Kullanıcı kararı: kapsam "şirket genelinde tek ayar" (Çalışma Tipi bazlı değil), üç seçenek
şimdi uygulansın (N Gün Eşiği dahil). `Sirket.raporlu_politikasi` (`tam_ode`/`hic_odeme`/
`n_gun_esigi`) + `Sirket.raporlu_esik_gun` alanları eklendi (migration `c3f7a2e91d05`,
varsayılan `hic_odeme`/`0` — mevcut şirketler için davranış değişmedi).

`payroll_calc.hesapla()` artık `raporlu_politikasi`/`raporlu_esik_gun` parametreleri alıyor:
- `tam_ode` → Yıllık İzin gibi, Ç.GÜN'den hiç düşmez.
- `hic_odeme` → Devamsız gibi, tamamı düşer (varsayılan).
- `n_gun_esigi` → ardışık her rapor bloğu (`_raporlu_dusen_gun_sayisi`) ayrı sayılır, her
  bloğun ilk `esik_gun` günü ödenir, kalanı düşer ("belli bir günün üzerini SGK ödüyor").
  **Bilinen Faz-1 sınırlaması:** bir rapor bloğu ay sınırını aşarsa, `hesapla()` sadece o ayın
  girişlerini gördüğü için blok her ayda yeniden N'den başlar — çok aylık rapor blokları için
  gelecekte ayrı bir çözüm gerekebilir.

Yeni izin anahtarı `sirket_ayarlarini_yonetebilir` (yalnızca `admin`) + `GET`/`PUT /api/sirket`
route'u (`app/api/routes/sirket.py`, audit log'a yazıyor) + frontend `CompanySettingsPage.tsx`
(`/sirket-ayarlari`, nav'da "Şirket Ayarları"). Hem `puantaj.py::ozet()` hem
`excel.py::disa_aktar()` şirketin politikasını okuyup `hesapla()`'ya geçiriyor. Uçtan uca
tarayıcıda doğrulandı (kaydet → reload → kalıcı), `pytest` 25/25 yeşil.

**Yan bulgu (düzeltildi, bu işle ilgisiz):** `kullanicilar.py`/`puantaj.py`/`tatiller.py`'deki
üç adet `status_code=204` endpoint, güncel FastAPI'nin (0.116) "204 body içeremez" kontrolüyle
çakışıyordu (`response_model` eksikti) — bu, backend'in HİÇ başlamamasına yol açan gizli bir
regresyondu, muhtemelen bu endpoint'ler eklendiğinden beri sunucu tam yeniden başlatılmamıştı.
Üçüne de `response_model=None` eklenerek düzeltildi.

## Faz 2 — SaaS/On-prem Dağıtım

- [ ] **Portal SSO entegrasyonu** — SaaS modda kimlik doğrulama Portal'ın RS256 JWT'siyle
  yapılacak. **Somut mekanizma araştırıldı ve netleşti (CLAUDE.md §8.8, 2026-07-04)** — Portal
  kaynak kodu okunarak doğrulandı: rol ataması tamamen Portal admin panelinden yapılıyor,
  uygulama-bazında serbest metin bir rol listesi (`tenant_app_settings.roles`) var; bu listeyi
  Puantaj için `"admin,kullanici,gm"` yaparsak JWT'nin `role` claim'i birebir bizim `Rol.kod`
  değerlerimizle eşleşir, ayrı çeviri tablosu gerekmez. Kalan iş: `/api/sso/login` endpoint'i,
  `tenant_{slug}_puantaj` DB çözümlemesi, JIT kullanıcı kaydı, bugün eklenen Kullanıcılar
  sayfasının SaaS modda gizlenmesi — detaylar CLAUDE.md §8.8'de. `AuthProvider` arayüzü Faz 1'de
  bu geçişe göre soyutlandı (`core/security.py`) — yeni bir `PortalSSOAuthProvider` eklenecek, iç izin modeli
  (`Rol.izinler`) değişmeyecek.
- [ ] **SaaS Docker/Traefik deploy config** — DigitalOcean droplet, tenant-başına-DB deseni
  (`tenant_{slug}_puantaj`), `docker-compose.yml` + Traefik label'ları (bkz. SaaS CLAUDE.md §6).
- [ ] **On-prem Inno Setup + NSSM installer** — `E:\Mira\OperonSM\installer\` (operon_setup.iss +
  configure-postgres.ps1/configure-firewall.ps1/create-operon-env.ps1/drop-operon-db.ps1 +
  build.ps1 + backend/build/operon.spec) saha-doğrulanmış bir referans şablon; Windows Server
  2022'de Program Files'a yazma izni UAC ile tamamen kapalı olduğu için tüm değişebilir dosyalar
  ProgramData'ya gitmek ZORUNDA — bu iki-dizin kuralı (Program Files=salt-okunur kod,
  ProgramData=okunur/yazılır veri) Puantaj'ın installer'ında da BİREBİR uygulanacak. Ayrıca
  alınacak dersler: `--onedir` (ASLA `--onefile` — antivirüs/AV karantina + yavaş açılış riski),
  tek exe + CLI flag'lerle çok modlu davranış (`--install-only`/`--migrate`/`--open-ui`/sunucu —
  `--open-ui` masaüstü kısayolu çalışıyor mu diye kontrol edip gerekirse arka planda başlatıyor,
  "çift tıkla çalışsın" tam burada kuruluyor), `IsUpgrade()` kontrolüyle güncellemede
  DB-yıkıcı adımların atlanması, port-meşgulse otomatik sıradaki portu deneme, ayrı ve hafif bir
  "patch installer" (sadece config değiştirip servisi restart eden, kullanıcı verisine dokunmayan).
  **AMA birebir kopyalanmayacak bir tasarım hatası var — düzeltilerek alınacak (Opus review, 2026-07-04):**
  OperonSM'in `icacls "{commonappdata}\Operon" /grant "Users:(OI)(CI)M" /T /C` komutu TÜM
  ProgramData ağacına (== `.env` dahil) yerel Users grubuna geniş yazma/okuma izni veriyor.
  `.env` içinde hem rastgele üretilen `JWT_SECRET_KEY` hem de paylaşılan/hardcoded Postgres şifresi
  aynı dosyada — yani sunucudaki herhangi bir yerel kullanıcı JWT imzalama anahtarını okuyup token
  forge edebilir. Puantaj'da bunun yerine:
  1. **Kullanıcı-ayarları** (varsa gelecekte kendi LLM API key'i vb.) → `ProgramData\OperonPuantaj\user.env`,
     Users yazabilir.
  2. **Sistem sırları** (`JWT_SECRET_KEY`, `DATABASE_URL`/DB şifresi) → `ProgramData\OperonPuantaj\secure\system.env`,
     yalnızca SYSTEM + Administrators + servis kimliği — Users bu dosyaya HİÇ erişemez. `icacls`
     çağrısı tek bir geniş `/T /C` yerine, `secure\` alt dizinine dar/ayrı bir ACL uygulamalı.
  3. **DB şifresi kurulum başına rastgele üretilmeli** (OperonSM'deki gibi ürünler arası paylaşılan
     sabit şifre — `Mm3471891298` — DEĞİL), ve Postgres superpassword/servicepassword/`DATABASE_URL`
     parametrelerinin ÜÇÜ DE aynı üretilen değerden beslenmeli (tek kaynak, drift riski olmasın).
  4. Mümkünse API key girişi UI üzerinden servise (SYSTEM olarak çalışan) yaptırılmalı — o zaman
     kullanıcının dosya sistemine hiç yazma izni gerekmez, ACL tamamen kilitlenebilir.
  Bu prensip Puantaj'dan itibaren TÜM yeni ürünlerde standart olacak; mevcut ürünlerde (OperonSM
  dahil) değişim maliyetine göre ayrıca değerlendirilecek — bu iş kapsamında DEĞİL.
- [ ] **Admin ilk-girişte parola değiştirme zorunluluğu** — seed `admin` kullanıcısının düz
  metin dev şifresi (`alembic/versions/..._seed_admin_user.py`) üretimde kabul edilemez.

## Kurulum Sihirbazı (Setup Wizard) — ✅ TAMAMLANDI (2026-07-04)

`SetupWizardPage.tsx` (5 adım: Şirket → Kurulum Modu → Admin Hesabı → [Çok Kullanıcı ise]
Maaş Görünürlüğü → Özet) + backend `POST /api/setup/complete` / `GET /api/setup/status`
(auth gerektirmez, "hiç Kullanici yok" = kurulum tamamlanmamış demek). `SetupGate.tsx`
uygulamanın en dışında — kurulum tamamlanmadan login ekranı bile gösterilmez.

Rol üçlüsü kod tabanına işlendi: `admin` (tam yetki) / `kullanici` (sadece puantaj girer,
`gorebilir_maas_tutari` wizard'da Admin'in seçtiği bir değer, varsayılan gizli) / `gm`
(tam görünürlük + export, sıfır yazma — `puantaj_girebilir`, `*_yonetebilir`,
`excel_ice_aktarabilir`, `donem_temizleyebilir` hepsi false). Eski `ik_personeli`/
`ik_yoneticisi` adları koddan tamamen kaldırıldı (`app/core/permissions.py`,
seed migration `81f9c9647f37`, hardcoded admin-seed migration silindi).

Uçtan uca doğrulandı (Playwright, tarayıcıda): taze DB → wizard 5 adım → otomatik giriş →
boş grid → Excel Aktarım'dan gerçek BESIM.xlsx yükleme → grid dolu, sıfır konsol hatası.

**Bağlantı noktası, henüz yapılmadı:** Wizard'ın ürettiği kararlar on-prem installer'ın
(yukarıdaki madde) ilk-kurulum akışına (OperonSM'deki `first_install.py` deseni) henüz
bağlanmadı — şu an sadece "uygulama ilk açıldığında tarayıcıda çalışan" bir akış, Inno
Setup/NSSM ile paketlenmiş .exe akışına entegre değil. SaaS modda bu wizard hiç çalışmaz
(kullanıcı/rol yönetimi Portal'dan yapılır), ama izin şeması (`Rol.izinler`) birebir aynı
kalmalı — bu ilke korundu, kod değişmedi.

## Faz 2 — Excel Onboarding Aracı

- [ ] **AI destekli konuşmalı mapping sihirbazı** (Schema-Adapt-Agent-lite) — OperonPI'nin
  `SCHEMA_ADAPT_SPEC.md`'i ve AILens PI'nin `mapping_chat_service.py`'i referans alınarak;
  Faz 1'de mekanizma (`ExcelMappingConfig` + `excel_adapter.py`) hazır, sadece onu ÜRETEN araç yok.
  Murat + Claude'un manuel süreci (CLAUDE.md §3) önce internal bir araca dönüştürülmeli.
  **İlk yapı taşı atıldı (2026-07-04, CLAUDE.md §8.3a):** `backend/scripts/excel_kesif.py` —
  yeni müşteri Excel'ini (sheet listesi, header adayları, TOPLAM satırı, ham örnek satırlar)
  otomatik-tahminsiz döken bir keşif scripti, BESIM.xlsx'te doğrulandı. Kalan iş: alan-eşleme
  önerisi + güven skoru + insan onay döngüsü (asıl "sihirbaz" kısmı).
- [ ] **Mapping versiyonlama** — müşteri Excel şeması değiştiğinde `mapping.v1` → `v2` geçişi,
  eski dönemler eski mapping ile okunmaya devam etmeli (OperonPI spec'inin Karar 4'ü).
- [ ] **Import/export mapping'in simetrik-olmayan durumu** — Faz 1 %99 vakayı (aynı dosya,
  aynı yapı) hedefliyor; roster ve çıktı sayfaları ayrı yapıdaki müşteriler için ayrı
  okuma/yazma config'i gerekebilir (CLAUDE.md §7'de kapanan karar, ama istisna çıkarsa revize edilir).

## Faz 2 — Güvenlik / Şeffaflık

- [x] **Maaş görünürlüğü — ✅ ÇÖZÜLDÜ, Kurulum Sihirbazı ile (CLAUDE.md §8.7, 2026-07-04)**
  Tek Kullanıcı'da otomatik (Admin zaten her şeyi görür). Çok Kullanıcı'da onboarding-zamanı
  dosya-incelemesi YERİNE, wizard'da Admin'e açık soru soruluyor ("Kullanıcı rolü maaş
  tutarlarını görebilsin mi?", varsayılan Hayır) — `POST /api/setup/complete` bunu
  `kullanici` rolünün `gorebilir_maas_tutari` alanına yazıyor. Kod tamam, tarayıcıda
  doğrulandı.
- [x] **Maaş sızıntısı sertleştirmesi — ✅ UYGULANDI (2026-07-04).** Denetim: `gorebilir_maas_tutari`
  şu ana kadar yalnızca `personel.py` listele ve `puantaj.py ozet()`'te uygulanıyordu; `excel.py
  disa_aktar()` (₺ tutarını Excel'e yazıyor) ve `audit.py listele()` (Personel maaş
  değişikliklerinin ham eski/yeni değerini `changes` alanında taşıyor) bu izne HİÇ bakmıyordu —
  seed rollerde (`admin`/`gm`) `excel_disa_aktarabilir`/`audit_gorebilir` her zaman
  `gorebilir_maas_tutari` ile birlikte geldiği için sızıntı görünmüyordu, ama bu rastlantıydı,
  kural değildi. Gelecekteki Rol Yönetimi UI'ı (aşağıda) bu izinleri bağımsız checkbox olarak
  sunacağı için gerçek bir risk oluşturuyordu. Kullanıcı kararı: "export/audit, maaş göremeyene
  tamamen kapalı" (alan bazlı maskeleme değil, route seviyesinde tam kilit). Çözüm:
  `core/security.py::require_permission()` artık birden fazla izin anahtarı alabiliyor (AND) —
  `disa_aktar` artık `EXCEL_DISA_AKTARABILIR` VE `GOREBILIR_MAAS_TUTARI` ikisini birden istiyor,
  `audit.py listele()` de `AUDIT_GOREBILIR` VE `GOREBILIR_MAAS_TUTARI` istiyor. Canlı API testiyle
  doğrulandı (`gorebilir_maas_tutari=False` olan bir role geçici olarak export/audit 403 döndü,
  geri `True` yapılınca 200'e döndü); `pytest` 25/25 yeşil, tarayıcıda admin akışı regresyonsuz.
- [x] **`/güvenlik` şeffaflık sayfası — ✅ UYGULANDI (2026-07-04).** Kullanıcı kararı: ayrı bir
  "Security Center" sayfası değil — mevcut Denetim Kaydı sayfası `/güvenlik`'e dönüştürüldü
  (tekrar yok, tek nav maddesi). İki parça:
  1. **Admin'e (ve maaş görebilen role) görünen kayıt tablosu** — `AuditLogPage.tsx` →
     `GuvenlikPage.tsx`, `/denetim` → `/güvenlik`. Eksik olan "kim yaptı" bilgisi eklendi: backend
     (`api/routes/audit.py`) artık `aktor_kullanici_id`'yi `Kullanici.ad_soyad`'a çözüp
     `aktor_adi` alanı olarak dönüyor (önceden sadece ham ID vardı, hiç gösterilmiyordu bile).
     Erişim aynı sıkı kural: `AUDIT_GOREBILIR` + `GOREBILIR_MAAS_TUTARI` ikisi birden.
  2. **Puantaj girişi yapanlara şeffaflık bildirimi** — kullanıcı: "puantaj girişleri yapanlara
     da işlemlerin kayıt altında olduğunu açıkça ifade etmemiz gerekli". `AttendanceGridPage.tsx`
     artık `audit_gorebilir` izni OLMAYAN kullanıcılara (kendi kaydını göremeyenlere) grid'in
     üstünde küçük, kalıcı bir bilgi notu gösteriyor: "Bu ekrandaki tüm işaretlemeler ve
     değişiklikler, kim tarafından ve ne zaman yapıldığı bilgisiyle birlikte kayıt altına
     alınmaktadır." Admin/GM bu notu görmüyor (zaten kaydı görebiliyorlar).
  Tarayıcıda uçtan uca doğrulandı: admin → aktör adı doğru çözülüyor, banner görünmüyor;
  `kullanici` rolü → banner görünüyor, nav'da Güvenlik linki yok, `/güvenlik`'e direkt gidiş
  ana sayfaya yönlendiriliyor. `pytest` 25/25 yeşil, sıfır konsol hatası.
- [x] **Audit log hacim/arşivleme stratejisi — kullanıcı kararıyla KAPANDI (2026-07-04).**
  "Bu konu benim için /güvenlik özelliğiyle kapandı" — ayrı bir partition/arşivleme çalışması
  yapılmayacak; düz tablo + index (Faz 1'deki mevcut hâli) yeterli kabul edildi.

## Faz 2 — Ürün Özellikleri

- [x] **Kullanıcı yönetimi (Rol Yönetimi) — ✅ UYGULANDI (2026-07-04).** Kullanıcı kararı: bu madde
  YENİ rol *tipi* tanımlamak değilmiş (Admin/Kullanıcı/GM üçlüsü sabit kalıyor) — "Admin yetkisi
  kimdeyse, o programa giriş yapacaklara yetki verebilsin diye var: +Ekle ile kullanıcı adı/şifre
  belirler, yetkisine (rolüne) karar verir." Oluşturma zaten vardı (`Kullanıcılar` sayfası);
  eksik olan mevcut bir kullanıcının rolünü/durumunu SONRADAN değiştirebilmekti — backend'de
  zaten hazırdı (`PUT /api/kullanicilar/{id}`, `POST .../parola-degistir`), sadece frontend UI'ı
  yoktu. `UsersRolesPage.tsx`'e Çalışma Tipleri'ndeki inline-edit deseniyle eklendi: rol
  değiştirme, ad/e-posta düzenleme, aktif/pasif toggle, ayrı bir dialogla şifre sıfırlama.
  Kendi hesabını pasife alma UI'da engellendi (checkbox disabled). Uçtan uca tarayıcıda
  doğrulandı (rol değiştir → GM, şifre sıfırla, pasife al, kendi satırında checkbox kilitli),
  sıfır konsol hatası.
- [x] **Çalışan Tipi bazlı FM oran özelleştirmesi — ✅ UYGULANDI (2026-07-04).** Kullanıcı kararı:
  "FM oran kısmı parametrelerin ayarlandığı sayfadan ayarlanmalı" — ayrı bir ayar sayfası değil,
  zaten parametrizasyon mekanizması olan Çalışma Tipleri sayfasına eklendi (CLAUDE.md §7).
  `CalismaTipi` modeline `hafta_ici_fm_orani`/`hafta_sonu_fm_orani` eklendi (varsayılan 1,5/2,0 —
  önceki sabit davranışla birebir aynı, migration `d94e6b3c7a12`), `payroll_calc.fm_orani()`
  artık bu iki parametreyi alıyor. `puantaj.py ozet()` ve `excel.py disa_aktar()` ilgili
  personelin Çalışma Tipi'nden bu oranları okuyup geçiriyor. `EmployeeTypesPage.tsx`'e iki yeni
  inline-edit kolonu eklendi. Doğrulama: `pytest` 26/26 yeşil (yeni test:
  `test_calisma_tipi_bazli_ozel_fm_orani`); canlı API'de bir tipin oranı geçici olarak
  ikiye katlanıp `fm_tl`'nin de tam ikiye katlandığı, sonra eski değerin doğru geri döndüğü
  doğrulandı; tarayıcıda inline edit round-trip (kaydet → değer kalıcı → varsayılana dön)
  sıfır konsol hatasıyla doğrulandı.
- [x] **Onay iş akışı — kullanıcı kararıyla KAPSAM DIŞI bırakıldı (2026-07-04).** "Bir onay
  akışına gerek yok" — submit/approve/reject state machine'i inşa edilmeyecek. Mevcut rol bazlı
  görünürlük (GM her şeyi görür, onaylama adımı olmadan) yeterli kabul edildi.
- [x] **Yıllık izin bakiyesi — kullanıcı kararıyla KAPSAM DIŞI bırakıldı (2026-07-04).** Puantaj,
  yıllık izin HAKEDİŞİNİ (accrual) hiç yönetmeyecek — bu müşterinin kendi İK/ETA sürecinin işi.
  Kural: müşterinin ilettiği kaynak veride önceden birikmiş bir bakiye varsa, Puantaj sadece
  KULLANIMI işaretler ve o bakiyeden düşer (bu zaten mevcut `yillik_izin` `gun_durumu` mekanizması
  — CLAUDE.md §2 ürün tezi "ETA'nın yerine geçmiyoruz" ile birebir uyumlu); kaynak veride bakiye
  hiç yoksa, konu tamamen kapsam dışı kalır. "Hakkı olmayana yıllık izin yazılmasını engelle" gibi
  bir doğrulama kuralı da BİLİNÇLİ OLARAK eklenmedi — kullanıcının kendi iş tecrübesi (Kasım'da işe
  başlayıp resmen hak etmeden Temmuz'da izin kullanan çalışanlar) bu kuralın gerçek hayatta pratikte
  tutmadığını gösteriyor; sabit bir "N ay çalışmadan izin yok" varsayımı hatalı olurdu.
- [x] **ETA'ya doğrudan aktarım — kullanıcı kararıyla KAPSAM DIŞI, sadece altyapı hazır tutulacak
  (2026-07-04).** ETA, onlarca farklı bordro/muhasebe programından yalnızca biri — proaktif
  genel bir özellik olarak inşa EDİLMEYECEK, yalnızca belirli bir müşteri özellikle isterse
  o müşteriye özel eklenecek. **Gerekli altyapı zaten mevcut, ek mimari çalışma gerekmiyor:**
  `ExcelMappingConfig` + `excel_adapter.py`'nin mapping-tabanlı export mekanizması (CLAUDE.md §3)
  müşteri Excel'ini nasıl esnek okuyup yazabiliyorsa, ETA'nın (veya Logo/Netsis/Mikro gibi
  herhangi bir başka programın) beklediği kolon/sayfa düzenine göre yazan bir export mapping'i
  de aynı mekanizmayla, YENİ bir sistem kurmadan tanımlanabilir — ihtiyaç doğduğunda sadece o
  müşteriye özel bir `ExcelMappingTemplate` kaydı eklenir. README'de (aşağıda oluşturuldu) bu
  yeteneğin mümkün olduğu, ama proaktif bir özellik olmadığı belirtildi.

## Teknik Borç

- [x] **Frontend bundle code-splitting — ✅ UYGULANDI (2026-07-04).** Giriş ve ana Puantaj grid'i
  (kritik yol) eager kalıyor, geri kalan 6 sayfa (`Personel`/`Çalışma Tipleri`/`Kullanıcılar`/
  `Excel Aktarım`/`Şirket Ayarları`/`Denetim Kaydı`) `React.lazy()` + tek bir `Suspense` sınırıyla
  (`App.tsx`) ayrı chunk'lara bölündü. Tek 535KB chunk yerine en büyük chunk artık 416KB
  (`index-*.js`, uygulama çekirdeği + grid), sayfa chunk'ları 1-7KB aralığında;
  `chunkSizeWarningLimit` uyarısı artık çıkmıyor. Tarayıcıda tüm sayfalar arası gezinme
  hatasız doğrulandı (Playwright, sıfır konsol hatası).
- [x] **Excel çoklu-mapping-template senaryosu — ✅ NETLEŞTİRİLDİ (2026-07-04), kod değişikliği
  gerekmedi.** Analiz: `ExcelMappingTemplate.sirket_id` zaten `Optional` bir FK — hem şirkete özel
  hem paylaşılan (`sirket_id=None`, ör. gömülü BESIM şablonu) şablonlar aynı anda var olabiliyor,
  ve bir şirketin BİRDEN FAZLA şablonu olmasını engelleyen bir unique kısıt yok (`sablonlari_listele`
  ikisini birden döner). Import/export her çağrıda `mapping_template_id`'yi açıkça parametre olarak
  alıyor (state olarak saklanmıyor) — yani "aynı anda birden fazla şablon" senaryosu Faz 1 modelinde
  zaten çalışıyor (ör. bir şirketin farklı departmanları farklı Excel düzeni kullanıyorsa, kullanıcı
  `SettingsPage`'deki dropdown'dan doğru şablonu seçer). Asıl "çoklu müşteri" endişesi (Faz 1
  mimarisi tenant-başına-DB olduğu için) bu DB içinde zaten yok — her kurulumda tek `Sirket` satırı
  var. Gerçekten açık kalan konu mapping VERSİYONLAMA (şema değişince v1→v2 geçişi) — bu zaten ayrı
  bir madde olarak yukarıda (Faz 2 — Excel Onboarding Aracı) takip ediliyor, burada tekrar edilmedi.

## Notlar

Bu liste `CLAUDE.md`'deki keşif sohbetinin doğal devamıdır — mimari kararların *neden*i için
oraya bakın, *ne* yapılacağının listesi burada.
