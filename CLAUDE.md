# CLAUDE.md — Operon Puantaj

> Bu dosya, kod yazımı başlamadan önceki keşif/tartışma sohbetinin bağlamını korumak için oluşturuldu.
> Amaç: sohbet uzadıkça veya yeni oturum açıldıkça buradan devam edebilmek. Kararlar netleştikçe
> güncellenmeli; "Açık Sorular" bölümü kapandıkça "Onaylanan Kararlar"a taşınmalı.

---

## 1. Proje Kimliği & Köken

- Bu iş, Murat'ın eşi **Emine** için günlük yazılmış bir HTML prototiple başladı (`Puantaj.html`).
- `BESIM.xlsx` — Emine'nin çalıştığı şirketin **gerçek** maaş/puantaj dosyası. **Sadece örnek** —
  ürünün hedef şeması DEĞİL. Her müşterinin kendi Excel düzeni farklı olabilir.
- Şimdi hedef: tam ürün — frontend + backend + kendi DB'si, **çok kullanıcılı** (aynı şirket
  içinde farklı roller), **on-premise VEYA SaaS** olarak çalışabilen.
- Ürün ailesi: Operon (kolektif360). Bkz. `E:\Mira\Kolektif360\Tasarim_İlkeleri\kolektif360-base.instructions.md`.

## 2. Ürün Tezi

> "ETA'nın yerine geçmiyoruz; ETA'ya girecek temiz, doğru puantajı üreten eksik katmanız."

- Non-invasive: müşterinin mevcut Excel/ETA düzenini değiştirmez, besler.
- Lokal & egemen: maaş en hassas veridir.
- Segment: 10–200 kişilik, puantajı hâlâ Excel'de tutan KOBİ.
- Günlük kullanıcı: sıfır teknik bilgili İK/ofis çalışanı. İkincil: onaylayan/patron.
- Guardrail'ler (Puantaj_Brief.md Bölüm 3): görünmez karmaşıklık, tek ekran disiplini, ucuz
  evrilebilirlik, RBAC matrisi kurmadan basit rol modeli.

## 3. En Kritik Mimari Prensip: Excel-Agnostiklik

**BESIM.xlsx bir örnek, hedef şema değil.** Ürünün korunması gereken tek sabit unsuru UX'idir:
takvim/grid ekranı (sol tık = gelmedi, sağ tık = izin/FM popover, sağda canlı özet kolonları).
Excel okuma/yazma bir **adaptör katmanı** — müşteriye göre değişken bir mapping config üzerinden çalışmalı.

**Mapping nasıl üretiliyor (kritik karar):** Bu runtime'da çalışan canlı bir YZ özelliği DEĞİL.
Kurulum/onboarding sırasında bir kereye mahsus bir süreç: müşteri Excel'ini kolektif360'a gönderir,
Murat + Claude (MQ_v3'teki Smart Template System deseniyle) mapping'i çıkarır, onaylanır, ürüne
statik bir JSON template olarak yüklenir. **Üretim ortamındaki uygulama örneği, müşteri maaş
verisiyle hiçbir LLM/relay çağrısı yapmaz** — bu, "veri müşteri ortamından çıkmaz" ilkesiyle SaaS
modunda bile tam uyumlu.

MQ_v3 deseni (bkz. `E:\Mira\MQ_v3\SMART_TEMPLATE_SYSTEM_COMPLETE.md`): Claude yüklenen dokümanı
tarar, alanları `STATIC / DB_AVAILABLE / USER_INPUT` diye kategorize eder, JSON `field_mappings`
üretir, insan onaylar. MQ_v3'te sadece **export** yönü var (DB → PDF/Excel template). Puantaj'da
ek olarak **import** yönü de gerekiyor (müşteri Excel → iç şema). Import ve export mapping'in aynı
obje mi ayrı obje mi olacağı henüz netleşmedi (bkz. Açık Sorular).

## 4. İş Mantığı — Bordro Hesap Kuralları

(Puantaj_Brief.md Bölüm 5'ten, `Puantaj.html`'deki `hesapla()`/`hesaplaGen()` fonksiyonlarıyla
karşılaştırılıp **doğrulandı** — birebir örtüşüyor.)

```
saatlik_ücret = (MAAŞ / N.G) / 7.5        # N.G çoğunlukla 30; günde 7,5 saat
Ç.GÜN         = N.G − (tam_gün_devamsızlık_sayısı)   # min 0
G (gün maaşı) = (MAAŞ / N.G) × Ç.GÜN

İZİN.TL       = toplam_izin_saati × saatlik_ücret          # 1,0×, hak edişten düşülür

FM.TL         = Σ_gün( fm_saat_gün × saatlik_ücret × (pazar_veya_tatil ? 2 : 1,5) )
                # izin ile KARIŞMAZ, ayrı kova; hafta içi ×1,5, Pazar/resmi tatil ×2

HAKEDİŞ       = PRİM + FM.TL + G − İZİN.TL
BANKA_net     = TOPLAM − AVANS − İCRA − BES        # TOPLAM = HAKEDİŞ + AGİ(0)
```

**Test vakaları (elle doğrulandı, tutuyor):**
- maaş 32000, N.G 30 → saatlik 142,2222 → 4s FM hafta içi + 3s FM Pazar → FM.TL=1.706,67; 2s izin → İZİN.TL=284,44
- maaş 50000, 2 gün devamsız → Ç.GÜN=28, G=46.666,67
- 19 Mayıs tatil, 5s FM ×2, saatlik 142,2222 → 1.422,22

**BESIM.xlsx doğrulama notu:** `HAZİRAN 2026 BANKA` sayfasında TOPLAM satırı SUM aralıkları doğru
(`C56=SUM(C3:C55)` vb.) — brief'in bahsettiği geçmiş hata bu ayda zaten düzeltilmiş, sağlıklı referans.

## 5. Prototip (`Puantaj.html`) — Teknik Notlar

- Tek dosya, ~968KB — büyük kısmı gömülü ExcelJS kütüphanesi (1. `<script>` bloğu). Gerçek app JS,
  son `<script>` bloğunda (~955.495. karakterden itibaren, ~280 satır).
- State: `localStorage`'da tutuluyor, key: `puantaj::{fileName}::{sheetName}`.
- Personel/N.G tespiti: `B` kolonunda "TOPLAM" yazısına kadar olan satırlar personel; N.G yoksa 30 varsayılan.
- **Export'ta iki sessiz davranış var — ürüne taşırken bilinçli karar gerekiyor:**
  1. O oturumda hiç işaretleme girilmemiş personelin `E/L/J/K` hücrelerine hiç dokunulmuyor
     (muhtemelen mevcut ETA/manuel değerleri korumak için — kabul kriteri #4 regresyon testiyle uyumlu).
  2. FM.TL=0 olduğunda `K` hücresine sayı değil `=J*I` formülü geri yazılıyor; >0 ise düz değer yazılıyor.

## 6. Referans Materyaller & Konumları

| Yol | İçerik |
|---|---|
| `E:\Mira\Operon_Puantaj\Puantaj_Brief.md` | Orijinal build brief — BESIM'e özel yazılmıştı, şimdi genelleştiriliyor |
| `E:\Mira\Operon_Puantaj\BESIM.xlsx` | Örnek müşteri dosyası (Emine'nin şirketi) |
| `E:\Mira\Operon_Puantaj\Puantaj.html` | Çalışan tek-dosya prototip |
| `E:\Mira\MQ_v3\SMART_TEMPLATE_SYSTEM_COMPLETE.md` | AI destekli şablon/mapping deseni (field_mappings JSON, STATIC/DB/USER_INPUT) |
| `E:\Mira\SaaS\CLAUDE.md` | kolektif360 SaaS platform mimarisi: tenant-başına-DB, Portal SSO (RS256 JWT), roller (`ik`/`lider` dahil), yeni-app-ekleme checklist'i |
| `E:\Mira\SaaS\PLANNERWS_RELAY_BRIEFING.md` | PlannerWS'in on-prem/standalone lisans modeli örneği (`OPERON-xxx` key, relay sadece kendi YZ asistanı için) |
| `E:\Mira\PlannerWS\src\ui\pages\TakvimSayfasi.tsx` | MUI takvim/grid UI referansı (786 satır, henüz detaylı incelenmedi) |
| `E:\Mira\Kolektif360\Tasarim_İlkeleri\` | kolektif360-base + frontend-design + brand guide + AI model API kılavuzu |

## 7. Onaylanan Kararlar

- **Excel adaptör mimarisi:** mapping onboarding-zamanı üretilir (Murat + Claude, insan onaylı),
  ürün çalışırken statik config olarak kullanılır. Runtime'da müşteri verisiyle LLM çağrısı yok.
- **SaaS/on-prem ikilisi:** müşteri tercihi, ikisinde de veri güvende. SaaS tarafı
  `E:\Mira\SaaS` platformuna uyumlu olacak (tenant-başına-DB deseni, Portal SSO).
- **Parametre sayfası:** izin günleri, günlük/aylık çalışma saat/gün gibi değerler değişebilir;
  varsayılanlar var ama kullanıcı override edebilir; **değişiklikler kayıt altına alınacak** (audit).
- **Çok kullanıcılılık anlamı:** aynı şirket içinde farklı yetkideki kullanıcılar (multi-company/
  multi-tenant-in-one-instance DEĞİL — tenant izolasyonu DB seviyesinde, SaaS modelinde olduğu gibi).
- **Rol isimleri (v1):** `IK Personeli` (girer), `IK Yöneticisi`, `GM` (onaylayan/üst yönetim).
  Sabit 2 rol değil — **müşteri kadro yapısına göre sonradan uyarlanabilir/genişletilebilir**
  olmalı (bkz. Bölüm 8, extensible rol modeli mimari kararı).
- **Parametrizasyon modeli — "Çalışan Tipi" (üç katmanlı hiyerarşi DEĞİL):** Şirket, bir
  "+Ekle" ekranından çalışan tipleri tanımlar (varsayılan: **Beyaz Yaka (BY)** ve
  **Mavi Yaka (MY)** — çoğu şirkette bu ikisi zaten hep var ve genelde aynı parametrelerle
  çalışır; şirket isterse `Müdür` gibi ek tipler de tanımlayabilir). Her tipin kendi parametre
  seti var (günlük saat, haftalık gün — ör. MY 7,5 saat×6 gün, BY 8 saat×5 gün olabilir).
  Personel bir tipe atanır. **Müşterinin Excel'inde bu tipi belirten bir kolon olmak zorunda** —
  import mapping bunu da yakalamalı (bkz. Bölüm 3/8, mapping'e tip alanı eklenmeli).
- **Export kapsamı (kapandı):** dokunulmamış personelin hücrelerine dokunulmaz — dokunulmamış
  olması zaten "o ay eksik çalışma da mesai de yok, tam maaşını aldı" anlamına gelir. Prototip
  davranışı (Bölüm 5) birebir doğru, ürüne aynen taşınacak.
- **Import/export mapping (kapandı):** %99 ihtimalle **tek, simetrik mapping** — beklenen girdi
  Excel'in birebir aynısının puantaj hesabıyla doldurulmuş hali. Ayrı import/export config'e
  şimdilik gerek yok.
- **Auth zamanlaması (kapandı):** "Faz 1'de auth yok" kararı **geçersiz** — Murat auth'un tüm
  mimariyi etkilediğini, baştan karara bağlanması gerektiğini belirtti. Auth/DB/stack kararları
  bu oturumda netleştiriliyor (bkz. Bölüm 8).
- **Maaş verisi gizliliği politikası (kapandı, 2026-07-04, wizard tartışmasıyla rafine edildi):**
  - **Tek Kullanıcı kurulumda:** basit otomatik kural — kaynak Excel'de maaş kolonu varsa
    görülür, yoksa görülmez. Tek kişi zaten Admin olduğu için gizlemenin anlamı yok.
  - **Çok Kullanıcı kurulumda:** otomatik çıkarım YOK — kurulum sihirbazında (bkz. Bölüm 8.7)
    Admin'e açık bir seçenek sunulur: "Kullanıcı rolü maaş tutarlarını görebilsin mi?"
    Admin karar verir, biz dosyaya bakıp sessizce karar vermeyiz.
  Mekanizma değişmedi: `Rol.izinler["gorebilir_maas_tutari"]`, `/api/puantaj/ozet` ve
  `/api/personel` alan-bazlı gizliyor (ikincisi 2026-07-04'te düzeltildi — önceden sadece
  geniş `puantaj_gorebilir` iznine bakıyordu, `maas` her zaman dönüyordu).
- **Maaş sızıntısı sertleştirmesi (kapandı, 2026-07-04):** `excel_disa_aktarabilir` ve
  `audit_gorebilir` izinleri artık `gorebilir_maas_tutari` olmadan işe yaramıyor — Excel export
  ₺ tutarı (`fm_tl`) yazıyor, denetim kaydı `Personel.maas` değişikliklerinin ham eski/yeni
  değerini taşıyor; seed rollerde (`admin`/`gm`) bu izinler hep birlikte geldiği için önceden
  sızıntı görünmüyordu ama bu rastlantıydı, kural değildi — Rol Yönetimi UI'ı (ROADMAP.md) bu
  izinleri bağımsız checkbox yapınca gerçek risk olurdu. Kullanıcı kararı: alan bazlı maskeleme
  değil, route seviyesinde tam kilit — `core/security.py::require_permission(*keys)` artık
  birden fazla izni AND ile isteyebiliyor.

## 8. Açık Sorular / Devam Eden Tartışmalar

### 8.1 Maaş verisi gizliliği — KAPANDI (bkz. Bölüm 7)
Politika karara bağlandı (Bölüm 7'ye taşındı — kaynak Excel'de maaş var/yok kuralı). Genel soru
kısmen hâlâ açık: hassas Excel çıktısı nerede duracak, kim görebilecek, dışarı sızma riskine
karşı ne önlem (indirilen dosyanın maillenmesi gibi senaryolar) alınacak — bkz. ROADMAP.md
`/guvenlik` şeffaflık sayfası maddesi.

### 8.2 Mimari sorular — KAPANDI (2. tur)
1. **DB motoru:** ✅ **PostgreSQL, her iki modda da** (SaaS ve on-prem). Tek ORM/migration/lehçe.
2. **On-prem dağıtım şekli:** ✅ Electron değil. **Inno Setup + NSSM + native Windows PostgreSQL
   servisi** — MQ_v3 ve OperonPI'nin kanıtlanmış deseni (`installer/*.iss`, `install-service.ps1`,
   bundled `postgresql-18.1-2-windows-x64.exe`, NSSM ile FastAPI backend Windows servisi olarak
   kayıtlı, `DependOnService` ile Postgres'e bağımlı). Frontend derlenip backend'den servis edilir,
   tarayıcıdan (localhost veya LAN IP) erişilir — Docker Compose DEĞİL. SaaS tarafı (DigitalOcean +
   Traefik + Docker, bkz. Bölüm 6) farklı paketleme kullanır ama **uygulama kod tabanı ortak**.
3. **Auth mimarisi:** ✅ **Puantaj kendi iç genişletilebilir rol/izin tablosunu tutar.** SaaS modda
   kimlik doğrulama Portal SSO (RS256 JWT), on-prem modda yerel kullanıcı adı/şifre — ama iç
   rol/izin modeli iki modda da aynı kod yolunu kullanır (kimlik doğrulama adaptörü değişir, izin
   modeli değişmez). Bu, "maaş görme izni" gibi ince taneli izinleri (bkz. 8.1) doğal destekler.

### 8.3a Onboarding Keşif Aracı — ✅ UYGULANDI (2026-07-04)

Kullanıcı: "bence en kritik konu, şekli ne olursa olsun programımızın exceli anlayabilmesi" —
mapping çıkarma sürecinin ilk adımı olan "ham veriyi görme" adımını hızlandırmak için
`backend/scripts/excel_kesif.py` eklendi. Murat + Claude yeni bir müşteri Excel'iyle
oturduğunda (CLAUDE.md §3'teki onboarding sohbeti) bu script çalıştırılır:

```
python scripts/excel_kesif.py "path/to/musteri.xlsx" [--sheet-icerir BORDRO --kimlik-kolon C ...]
```

**Ne yapar:** `excel_adapter.py`'nin GERÇEK runtime fonksiyonlarını (`list_matching_sheets`,
`find_toplam_row`) aynen kullanarak sheet listesini (eşleşen/eşleşmeyen), header satırı
adaylarını, TOPLAM satırının nerede bulunduğunu ve ilk N personel satırını kolon harfleriyle
birlikte (ham, formüller dahil) döker. BESIM.xlsx üzerinde test edildi — 15 sheet'ten 6 BANKA
sayfasını doğru ayırdı, header ("AD SOYAD"/"MAAŞ"/"FM.SAAT" vb.) ve TOPLAM satırını doğru buldu.

**Ne yapmaz (bilinçli sınır):** Hiçbir alanı (ad_soyad/maaş/ng/...) otomatik EŞLEMEZ veya
TAHMİN ETMEZ — CLAUDE.md'nin temel kuralı burada da geçerli. Çıktı sadece ham zemin; hangi
kolonun hangi alana karşılık geldiğine hâlâ insan+Claude konuşması karar verir, nihai
`ExcelMappingConfig` JSON'unu elle üretip `/api/excel/mapping-templates`'e yükler. Bu, ROADMAP.md'deki
"AI destekli konuşmalı mapping sihirbazı"nın TAMAMI değil — sadece ilk yapı taşı (keşif adımı);
alan-eşleme önerisi + güven skoru + onay döngüsü kısmı hâlâ Faz 2.

Windows notu: script `sys.stdout.reconfigure(encoding="utf-8")` kullanıyor — Windows konsolunun
varsayılan cp1254/1252 kod sayfası Türkçe karakterler ve ✅ gibi işaretlerle çakışıyordu.

### 8.3 Önemli precedent: OperonPI'nin "Schema Adapt Agent"ı
`E:\Mira\OperonPI\SCHEMA_ADAPT_SPEC.md` (988 satır) — bizim Excel-mapping problemimizin
olgunlaşmış büyük kardeşi. Her müşterinin ERP/MES verisi farklı kolon adlarıyla gelir; Claude ile
**tek seferlik API çağrısı değil, çok turlu bir konuşma** üzerinden müşteri şeması ortak bir
kanonik şemaya (OCMS — Operon Canonical Manufacturing Schema) eşlenir:
- Her kolon için güven skoru (HIGH/MEDIUM/LOW), belirsizlikte kullanıcıya soru sorulur (tahmin
  edilmez), her değişiklikten sonra 5 satırlık önizleme gösterilir, kullanıcı "Onayla" diyene kadar döngü.
- `schema_infer` tool'u tek kolonu izole görmez — `sibling_columns` + `previously_mapped`
  bağlamıyla çalışır (ör. "Date" kolonu sipariş tarihi mi başlangıç tarihi mi, komşu kolonlara bakarak anlaşılır).
- Çıktı: versiyonlanmış mapping JSON (`mapping.v1.json` → şema değişirse `v2`), önizleme, (OperonPI'de ayrıca SKILL.md/dashboard spec — bizde karşılığı yok).
- Session state, dosya şifreleme, retention/silme, kalibrasyon test seti gibi üretim-sertliği
  gereksinimleri var — OperonPI'de bile bunlar Faz 1-2'ye ayrılmış, tek seferde yapılmamış.

**Bizim için çıkarım:** Puantaj'ın "Excel Canonical Schema"sı (Ad Soyad, Maaş, N.G, Çalışan Tipi,
izin saat, FM saat, ...) için aynı deseni izlemek mantıklı — ama MVP'de OperonPI'nin tam
olgunluğuyla değil, daha sade bir versiyonla başlanmalı (bkz. Bölüm 3 — onboarding'de Murat +
Claude birlikte kullanır, önce müşteriye açık self-servis bir araç değil).

### 8.5 İkinci precedent: AILens PI — çalışan, üretimdeki bir ürün (yalnızca spec değil)
`E:\Mira\AILens_PI` — ERP/MES şema keşif aracı, OperonPI'a besleyici. Schema Adapt Agent
spec'inin (8.3) **gerçek, kodlanmış hâli**. Doğrudan devşirilebilir 4 parça:

1. **Veri modeli deseni** (`backend/app/models/mapping.py`) — `FieldMapping` (source_col,
   confidence, note), `RequiresReviewItem` (belirsiz alan + aday listesi + kullanıcı seçimi),
   üst düzey `AilensMapping` (versiyonlu, `draft`/`approved` durumlu, `privacy_report` alanlı).
   Puantaj'da birebir aynı şekil kullanılabilir — entity/tablo yerine Excel sayfası/kolonu.
2. **3 katmanlı anonimleştirme** (`sample_collector.py`) — regex tabanlı: `_PII_PATTERN`
   (ADI/SOYADI/EMAIL/PHONE/TCKNO/...) → `[GİZLİ]`, `_SENSITIVE_PATTERN` (PASSWORD/SIFRE) →
   tamamen atla, `_KEEP_VALUE_PATTERN` (CODE/REF/NO/TYPE/ID/...) → değeri koru (tanımlayıcı,
   PII değil). **Not:** Puantaj'da "Ad Soyad" zaten haritalanması gereken bir alan (PII maskesi
   burada işe yaramaz) — ama TCKNO/IBAN/telefon gibi Excel'de bulunabilecek başka kolonlar için
   aynı desen uygulanabilir; onboarding'de müşteri Excel'i Murat/Claude'a giderken bu maskeleme
   katmanından geçirilmeli.
3. **Güvenlik Merkezi sayfası** (`api/routes/security.py`, `/security`) — müşteriye şeffaflık:
   hangi verinin nereye gittiği, aktif gizlilik ayarları (local/cloud mod), LLM denetim günlüğü
   canlı gösterimi. **8.1'deki "maaş verisi nereye gidiyor, kim görebiliyor" endişesine doğrudan
   cevap veren bir ürün deseni** — Puantaj'a da benzer bir `/guvenlik` sayfası eklenebilir.
   Ayrıca AILens PI, salt-okunur DB rolünde HR tablolarını açıkça `DENY` ediyor
   (`DENY SELECT ON dbo.HR_EMPLOYEES`) — hassas veriyi varsayılan olarak dışarıda tutma pratiği.
4. **LLM denetim günlüğü** (`services/llm_audit.py`) — thread-safe ring buffer + opsiyonel
   JSONL disk yazımı, her kayıtta: zaman, çağrı tipi, model, local/cloud modu, web search
   kullanıldı mı, system/user/output önizlemesi (ilk 200-400 karakter). Puantaj'ın audit
   ihtiyacı farklı (puantaj girişi denetimi, LLM çağrısı değil) ama **kayıt şekli** (append-only,
   zaman damgalı, aktör + eski/yeni değer) doğrudan örnek alınabilir.

### 8.6 Henüz sorulmamış / netleşmemiş
- **Audit log kapsamı:** sadece parametre değişiklikleri mi, yoksa puantaj girişleri (kim hangi
  günü ne zaman işaretledi/değiştirdi) dahil genel bir denetim izi mi? (AILens PI'nin append-only
  log deseni — Bölüm 8.5/4 — muhtemel teknik çözüm, ama kapsam kararı hâlâ açık.)

### 8.8 SaaS Portal Entegrasyonu — ✅ UYGULANDI VE DEPLOY EDİLDİ (2026-07-05)

Kullanıcı: "admin.kolektif360.com'da tenant açıyoruz, o tenant'ın admini portal.kolektif360.com'a
girip yeni kullanıcı ekleme ve yetki vermeyi ORADAN yapıyor — bizim program bu tenant/yetki
bilgisini anlayıp ona göre davranmak zorunda." `E:\Mira\SaaS\apps\portal` kaynak kodu okunarak
(`app/services/jwt_service.py`, `app/routes/sso.py`, `admin/services/user_service.py`,
`admin/routes/tenants.py`) somut mekanizma doğrulandı:

**Rol ataması Portal'da, uygulama bazında SERBEST METİN:**
- `tenant_app_settings.roles` — her (tenant, app_slug) çifti için bir CSV string (örn.
  `"admin,user"`, varsayılan). **Sabit bir enum değil** — admin panelinin "Tenant → Manage"
  ekranında bu CSV istenildiği gibi ayarlanabilir.
- `user_roles` tablosu (`user_id, tenant_id, app_slug, role`) — admin, bu CSV'den seçerek her
  kullanıcıya UYGULAMA BAZINDA bir rol atar (admin panelinden, biz hiçbir şey yazmadan).
- Kullanıcı uygulamayı açtığında (`sso.py::launch_app`), Portal `user_roles`'tan O UYGULAMAYA
  özel rolü okuyup JWT'nin `role` claim'ine **aynen** koyar (`role=user_app_roles[app_slug]`).

**Sonuç — Puantaj için kritik kolaylık:** Puantaj'ı Portal'a tanıtırken (`provision_puantaj.py`)
`tenant_app_settings.roles` = `"admin,kullanici,gm"` olarak ayarlanırsa, Portal'dan gelen `role`
string'i **birebir bizim `Rol.kod` değerlerimizle aynı** olur — ayrı bir "Portal rolü ↔ Puantaj
rolü" çeviri tablosuna gerek YOK. JWT'deki `role` doğrudan yerel `Rol.kod`'a eşlenip mevcut
`SEED_ROL_IZINLERI`/izin modeli aynen kullanılabilir. §8.2/3'teki "izin modeli iki modda da aynı
kod yolu" hedefi bu sayede tam karşılanıyor.

**JWT akışı (SaaS CLAUDE.md §4.2-4.3, `jwt_service.py` ile doğrulandı):**
- Algoritma RS256, `aud`=app_slug (`"puantaj"`), claims: `sub` (portal user id), `tenant_id`,
  `tenant_slug`, `username`, `role`, `is_platform_admin`. TTL 2 saat.
- Kullanıcı portal'da "Aç"a basar → Portal auto-submit HTML form ile
  `https://puantaj.kolektif360.com/api/sso/login`'e POST eder → Puantaj JWT'yi Portal'ın public
  key'iyle doğrular (`iss`/`aud`/`exp` kontrolü) → `access_token` cookie set eder.

**Puantaj tarafında yapılanlar (2026-07-05, tek oturumda uçtan uca tamamlandı):**
1. **Dual auth-mode mimari:** `AUTH_MODE` env'i (`onprem` varsayılan | `saas`) — `core/database.py`
   ve `core/security.py`, `get_session`/`get_current_user`'ı import zamanında bu değere göre iki
   implementasyondan birine bağlıyor. Mevcut 10 route dosyası HİÇ değişmedi (hepsi zaten sadece
   `get_session`/`get_current_user` import ediyordu).
2. `app/services/portal_sso_service.py` — SaaS_Platform/apps/SRM'in kanıtlanmış `PortalSSOService`
   deseninin birebir kopyası (portal public key fetch+cache, RS256 doğrulama).
3. `app/core/tenant_db.py` — Multi-tenant DB çözümleme YAPILDI: JWT'deki `tenant_slug` →
   `tenant_{slug}_puantaj` DB'si lazy oluşturuluyor + **programatik `alembic upgrade head`**
   çalıştırılıyor (SRM'nin `create_all` deseninden farklı — Puantaj gerçek Alembic migration
   zincirini kullandığı için; seed migration da otomatik çalışıp Sirket+3 Rol satırını hazırlıyor).
   Bunun için `alembic/env.py`'de küçük bir düzeltme gerekti (programatik URL override'ı artık
   ezilmiyor).
4. **JIT (just-in-time) kullanıcı kaydı YAPILDI** (`core/security.py::get_current_user_saas`):
   ilk SSO girişinde JWT'deki `username`+`role` ile eşleşen yerel `Kullanici` yoksa otomatik
   oluşturuluyor, rol portal'da değişirse senkronize ediliyor.
5. **Kullanıcılar sayfası SaaS modda gizlendi** — hem backend route'u (`App.tsx`'te route hiç
   register edilmiyor) hem nav linki (`AppLayout.tsx`), `AUTH_MODE==='saas'` kontrolüyle.
6. `api/routes/sso.py` — `/api/sso/login` (cookie set) + `/api/sso/logout` (httponly cookie'yi
   backend'in temizlemesi gerekiyor, JS'ten silinemiyor).
7. Frontend: `VITE_AUTH_MODE` build bayrağı — `apiClient.ts` `withCredentials:true`,
   `AuthContext.tsx`'te SaaS modda `getToken()` kısa devresi kaldırıldı (aksi halde `/me` hiç
   çağrılmıyordu — cookie'yle çalışırken localStorage kontrolü anlamsız kalıyordu, gerçek bir
   bug'dı, test sırasında yakalandı).
8. Relay/billing/metering'e dokunulmadı — doğru karardı, Puantaj hâlâ hiç LLM çağrısı yapmıyor.

**Platform (portal) tarafı da tamamlandı:** `provision_puantaj.py`, `admin_apps.html` kartı,
`status_service.py` health-check girişi — hepsi `apps/portal`'a eklenip deploy edildi.

**Deploy edildi ve doğrulandı (2026-07-05):** `https://puantaj.kolektif360.com` canlı, Traefik +
Let's Encrypt sertifikası çalışıyor, gerçek Portal SSO akışıyla (admin panel "Aç" butonu) tarayıcıda
test edildi — grid ekranı, BESIM.xlsx içe aktarımı (mapping template zaten mevcut,
`data/seed/besim_mapping.json`'dan üretim tenant DB'sine eklendi), Excel'e Aktar butonu hepsi
çalışıyor.

**Önemli bulgu ve düzeltme:** Deploy sırasında SPA catch-all route'ta (`main.py`) path traversal
açığı (CWE-22) bulundu — `full_path` parametresi resolve edilip `_static` dizini altında kaldığı
doğrulanmadan dosya servis ediliyordu, bu da container içindeki herhangi bir dosyanın (`../../`
ile) okunabilmesine izin veriyordu. `candidate.resolve().is_relative_to(_static_resolved)`
kontrolüyle düzeltildi, hem yerelde hem üretimde doğrulandı.

**Yerleşim notu (kapandı, 2026-07-05):** İki farklı klasör olarak duran `E:\Mira\Operon_Puantaj`
ile `E:\Mira\SaaS\apps\Operon_Puantaj` (sembolik link DEĞİL, ayrı fiziksel kopyalar — birbirinden
kod bakımından senkron değildi çünkü bu oturumdaki tüm değişiklikler yalnızca SaaS\apps kopyasına
yazılmıştı) birleştirildi: **`E:\Mira\SaaS\apps\Operon_Puantaj` tek asıl (canonical) konum** olarak
kabul edildi, `E:\Mira\Operon_Puantaj` robocopy /MIR ile bununla eşitlendi (2026-07-05). Yeni
geliştirme yalnızca `E:\Mira\SaaS\apps\Operon_Puantaj` üzerinden yapılmalı.

### 8.10 Maaş Zammı — Geçmiş Bordroyu Bozan Kritik Açık — ✅ BULUNDU VE DÜZELTİLDİ (2026-07-06)

Kullanıcı sorusu: "yıllar boyunca sorunsuz çalışması için herşeyi düşünmeliyiz... maaşlara zam
gelince onu sisteme nasıl alacağız? Bu program sonradan puantaj konusundaki tek kaynak
olacaksa ona göre yapılanmalıyız." Kod taraması gerçek ve ciddi bir açık ortaya çıkardı:
`Personel.maas` tek bir "güncel" değerdi, hiçbir geçmiş/tarihçe tutmuyordu — `ozet()` ve
Excel export, hangi GEÇMİŞ dönem hesaplanıyor olursa olsun her zaman BUGÜNKÜ maaşı okuyordu.
Birine zam yapılınca (ör. Ağustos'ta) geçmiş ayların (ör. Haziran) bordrosu da tekrar
hesaplanırsa/dışa aktarılırsa yanlışlıkla yeni maaşla hesaplanırdı — N.G için Faz 4'te tam
olarak çözülen sorunun birebir aynısı ("dönem bazlı değer, ama sabit tutulan bir alanda
saklanıyor"), sadece maaş için hiç ele alınmamıştı.

**Çözüm (N.G'nin `PersonelDonemAyar` desenine benzer ama FARKLI semantikte):**
`PersonelMaasGecmisi` tablosu — etkin-tarihli (carry-forward): bir kayıt, girildiği (yıl,ay)'dan
itibaren bir SONRAKİ kayda kadar TÜM dönemlere uygulanır (N.G'nin istisnası SADECE o dönem
için geçerliydi, bu farklı). `efektif_maas()` resolver'ı hedef dönemden önceki/o döneme ait en
son kaydı bulur. `POST /api/personel/{id}/zam`, ilk kez zam giriliyorsa o ana kadarki maaşı
geçmiş dönemler için sabitleyen bir "taban" kayıt da otomatik ekliyor. `PersonelUpdate`'ten
`maas` alanı bilinçli olarak kaldırıldı — artık tüm maaş değişiklikleri etkin dönem
belirtilerek yapılmak zorunda. Excel export'ta MAAŞ kolonu da (N.G'deki gibi) müşterinin
kendi formülleri için güncelleniyor artık.

Canlı API'de uçtan uca doğrulandı (geçmiş dönem değişmedi, yeni dönem doğru maaşı kullandı),
tarayıcıda "Zam Gir"/"Geçmiş" UI'ı ile doğrulandı, sıfır konsol hatası — ayrıntılar
`CHANGELOG.md` Faz 4.8'de.

### 8.9 Yıl Geçişi Riski — Resmi Tatiller — ✅ BULUNDU VE HAFİFLETİLDİ (2026-07-06)

Kullanıcı sorusu: "bu yıl bitince 2027'ye geçince ne olacak?" Kod taranarak doğrulandı:

**Otomatik/sorunsuz olanlar:** Dönem seçici (`bugun.getFullYear()` her zaman güncel), `Donem.ng`
(`calendar.monthrange` her yılda çalışır), Excel sheet adı ayrıştırma/yeni-ay-sayfası-oluşturma
(yıl regex'i `20\d\d`, metin ara/değiştir dinamik) — hiçbiri hardcoded yıl içermiyor.

**Tek gerçek risk:** `VARSAYILAN_TATIL_2026` (`alembic/versions/81f9c9647f37_seed_data.py`) —
14 resmi tatil tarihi, kuruluşta BİR KEZ seed ediliyor. Dini bayramlar (Ramazan/Kurban) yıldan
yıla ~10-11 gün kaydığı için otomatik hesaplanamaz; kimse elle girmezse yeni yılın resmi
tatilinde çalışılan FM sessizce hafta içi oranıyla hesaplanır (düşük ödeme riski).

**Hafifletme:** `AttendanceGridPage.tsx`'e, seçilen dönemin yılında hiç `Tatil` kaydı yoksa
`tatil_yonetebilir` iznine sahip kullanıcılara bir uyarı banner'ı eklendi ("Tatilleri Gir"
butonuyla `HolidaysDialog`'u doğrudan açıyor). Otomatik tatil ÜRETİMİ yapılmadı (dini bayram
tarihleri güvenilir hesaplanamaz) — sadece sessiz hatayı görünür kılan bir uyarı. Gerçek 2027
dönemi oluşturulup tarayıcıda doğrulandı.

### 8.7 Kurulum Sihirbazı (Setup Wizard) — ✅ UYGULANDI (2026-07-04)

Murat'ın önerisi: kurulum sonrası ilk açılışta "göze hoş gelen" bir setup wizard, aşağıdaki
soruları sırayla sorar. **Bu, rol modelinde gerçek bir değişiklik gerektiriyor** — kozmetik
yeniden adlandırma değil.

**Adım 1 — Tek Kullanıcı / Çok Kullanıcı:**
- Çok Kullanıcı seçilirse kurulum **sunucuda olmak zorunda** (birden fazla kişi ağ üzerinden
  erişecek). Tek Kullanıcı, en yüksek yetkili kullanıcının kendi bilgisayarında da olabilir.
- Tek Kullanıcı → tek bir **Admin** hesabı otomatik oluşturulur, aynı rol/izin modeli korunur
  (SaaS ile tutarlılık ilkesi — CLAUDE.md §8.2/3 "iç izin modeli iki modda da aynı" kararıyla
  uyumlu, sadece hesap sayısı 1).

**Adım 2 — Çok Kullanıcı ise: roller ve izinler.**
Yeni üçlü (mevcut `ik_personeli`/`ik_yoneticisi`/`gm` seed'inin yerini alıyor — 3 rol sayısı
aynı kalıyor, ama semantik değişiyor):

| Rol (yeni) | Eski karşılığı | Görür mü | Yazar mı |
|---|---|---|---|
| **Admin** | `ik_yoneticisi` | Her şey | Her şey |
| **Kullanıcı** | `ik_personeli` | Sadece puantaj; maaş **varsayılan gizli** | Sadece puantaj girişi |
| **GM** | `gm` (semantik DEĞİŞTİ) | Her şey (maaş dahil) | **Hiçbir şey** — export/rapor indirme hariç (export "yazma" sayılmaz, kendi verimizi değiştirmiyor) |

**Maaş görünürlüğü — çelişki çözüldü:** Önceki karar (Bölüm 7) "dosyada maaş varsa otomatik
göster" diyordu; Murat bunun Kullanıcı rolü için geçersiz olduğunu belirtti ("veride maaşlar
olsa da Kullanıcı göremez"). Çözüm: **Tek Kullanıcı**'da eski basit kural geçerli (dosyada
maaş var/yok → otomatik). **Çok Kullanıcı**'da otomatik çıkarım YOK — wizard'da Admin'e açık
bir checkbox ("Kullanıcı rolü maaş tutarlarını görebilsin mi?") sorulur, Admin karar verir.

**Değişmeyen ilke:** Wizard sadece **on-premise** kurulumu yönetir. SaaS modda kullanıcı/yetki
yönetimi Portal üzerinden ayrıca yapılır (CLAUDE.md §8.2/3) — ama **tenant ve rol/izin yapısı
birebir aynı** olmalı (`Rol.izinler` şeması, izin anahtarları) ki iki mod arasında geçiş
sorunsuz olsun.

**Uygulandı:**
1. `app/core/permissions.py` → `SEED_ROL_IZINLERI` yeni üçlüye göre güncellendi (`admin`,
   `kullanici`, `gm`; GM'nin tüm `*_yonetebilir`/`*_aktarabilir`/`donem_temizleyebilir`/
   `excel_ice_aktarabilir` bayrakları false, `excel_disa_aktarabilir` true).
2. Seed migration (`81f9c9647f37_seed_data.py`) yeni rol adları/izinleriyle güncellendi;
   hardcoded admin-user seed migration'ı tamamen kaldırıldı (wizard bu işi üstlendi).
3. Backend: `POST /api/setup/complete` + `GET /api/setup/status` (`api/routes/setup.py`,
   auth gerektirmez — "hiç Kullanici yok" = kurulum tamamlanmamış demek, ayrı bayrak yok).
4. Frontend: `SetupWizardPage.tsx` (5 adım, MUI Stepper + Fade geçişleri), `SetupGate.tsx`
   (uygulamanın en dışında, kurulum tamamlanmadan login bile gösterilmez), `ModeCard.tsx`.
5. Uçtan uca doğrulandı (Playwright, tarayıcıda, sıfır konsol hatası): taze DB → wizard →
   otomatik giriş → boş grid → gerçek BESIM.xlsx import → grid dolu.

**Henüz yapılmadı:** Wizard'ın ürettiği kararların on-prem installer'ın (Inno Setup/NSSM,
ROADMAP.md) ilk-kurulum akışına bağlanması — şu an sadece tarayıcıda ilk-açılış akışı,
paketlenmiş .exe'ye entegre değil. Ayrıntılar ROADMAP.md'de.

## 9. Çalışma Kısıtları (aktif)

- Windows + PowerShell, UTF-8 zorunlu (Türkçe karakterler her katmanda bozulmadan).
- Sohbet dili Türkçe, kod İngilizce.
- Tahmin etme, uydurma yasak — emin olmadığın bordro kuralında dur ve sor.
- **KOD YAZMA EN SON.** Şu an keşif/tartışma fazındayız — kullanıcı açıkça "önce beni iyi
  anlamalısın" dedi. Mimari netleşmeden implementasyona geçilmeyecek.
