import { useMemo, useState } from 'react'
import { Box, IconButton, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from '@mui/material'
import EditIcon from '@mui/icons-material/Edit'
import type { CalismaTipi, Donem, GunDurumu, Personel, PersonelOzet, PuantajGirisi, Tatil } from '../../services/types'
import { GRID_CIZGI_RENGI, TATIL_BASLIK_RENGI, TR_AYLAR, TR_GUN_KISA, gunSayisi, haftaTatiliMi, ymd } from '../../utils/date'
import { donemdeCalisiyorMu, gunCalisiyorMu } from '../../utils/personel'
import { VARSAYILAN_GUNLUK_SAAT } from '../../utils/saat'
import { DayCell } from './DayCell'
import { EntryPopover } from './EntryPopover'

const SUM_KOLON_GENISLIK = 64

// Not: özet kolonları (sağ taraf) bilinçli olarak sticky DEĞİL — kullanıcı
// geri bildirimi (2026-07-05): sağın sabit kalması istenmiyor, günlerle birlikte
// kaydırılsın. Günlerin sticky sütunların altında "kaybolma" riskine karşı asıl
// çözüm zaten kutunun kendi yatay kaydırma çubuğunun her zaman görünür olması
// (aşağıdaki maxHeight/overflow ayarı) — bu, sağ tarafı sabitlemeye gerek bırakmıyor.
const SOL_SABIT_GOLGE = '6px 0 6px -4px rgba(0,0,0,0.25)'

const OZET_KOLONLARI = [
  { key: 'cgun', etiket: 'Ç.GÜN' },
  // Kullanıcı geri bildirimi (2026-07-04): "izin saatlik hesaba giriyor ama
  // hiç gelmediyse maaş eksilmiyor gibi görünüyor" — hesap zaten doğruydu
  // (Ç.GÜN düşünce gün maaşı da düşüyordu), sadece hiçbir yerde ₺ olarak
  // görünmüyordu. Bu kolon devamsız+raporlu günlerin toplam maliyetini gösterir.
  { key: 'gun_maasi_kesintisi', etiket: 'Gün Kesintisi' },
  { key: 'yillik_izin_gun', etiket: 'Yıllık İzin' },
  { key: 'raporlu_gun', etiket: 'Raporlu' },
  { key: 'izin_saat', etiket: 'İzin s' },
  { key: 'izin_tl', etiket: 'İzin ₺' },
  { key: 'fm_saat', etiket: 'FM s' },
  { key: 'fm_tl', etiket: 'FM ₺' },
] as const

interface Props {
  donem: Donem
  personelListesi: Personel[]
  tipler: CalismaTipi[]
  girisler: PuantajGirisi[]
  ozetListesi: PersonelOzet[]
  tatiller: Tatil[]
  maasGorebilir: boolean
  personelYonetebilir: boolean
  onGunToggle: (personelId: number, tarih: string, mevcut: PuantajGirisi | undefined) => void
  onGunKaydet: (personelId: number, tarih: string, gunDurumu: GunDurumu, izinSaat: number, fmSaat: number) => void
  onGunTemizle: (personelId: number, tarih: string) => void
  onNgAyarla: (personelId: number, ng: number | null) => void
}

// Hesap motorunun backend varsayılanıyla aynı (payroll_calc.py — hafta_tatili_gunleri=frozenset({6})).
const VARSAYILAN_HAFTA_TATILI = [6]

export function PuantajGrid({
  donem,
  personelListesi,
  tipler,
  girisler,
  ozetListesi,
  tatiller,
  maasGorebilir,
  personelYonetebilir,
  onGunToggle,
  onGunKaydet,
  onGunTemizle,
  onNgAyarla,
}: Props) {
  const [popoverAnchor, setPopoverAnchor] = useState<HTMLElement | null>(null)
  const [aktifHucre, setAktifHucre] = useState<
    { personelId: number; calismaTipiId: number; tarih: string; ad: string; gun: number } | null
  >(null)
  const [ngDuzenlenenId, setNgDuzenlenenId] = useState<number | null>(null)
  const [ngGirisDegeri, setNgGirisDegeri] = useState('')

  const gun = gunSayisi(donem.yil, donem.ay)
  const gunler = useMemo(() => Array.from({ length: gun }, (_, i) => i + 1), [gun])
  const tatilSet = useMemo(() => new Set(tatiller.map((t) => t.tarih)), [tatiller])

  // Kullanıcı geri bildirimi (2026-07-04): işten çıkan personel çıktığı ayın
  // sonuna kadar listede kalır, sonraki aylarda düşer; yeni giren personel
  // işe başladığı aydan itibaren görünür.
  const gorunenPersonel = useMemo(
    () => personelListesi.filter((p) => donemdeCalisiyorMu(p, donem.yil, donem.ay)),
    [personelListesi, donem.yil, donem.ay],
  )

  const girisMap = useMemo(() => {
    const map = new Map<string, PuantajGirisi>()
    for (const g of girisler) map.set(`${g.personel_id}|${g.tarih}`, g)
    return map
  }, [girisler])

  const ozetMap = useMemo(() => {
    const map = new Map<number, PersonelOzet>()
    for (const o of ozetListesi) map.set(o.personel_id, o)
    return map
  }, [ozetListesi])

  const tipMap = useMemo(() => {
    const map = new Map<number, CalismaTipi>()
    for (const t of tipler) map.set(t.id, t)
    return map
  }, [tipler])

  function fmt(n: number): string {
    return n.toLocaleString('tr-TR', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
  }

  function ozetHucreIcerik(ozet: PersonelOzet | undefined, key: (typeof OZET_KOLONLARI)[number]['key'], ng: number) {
    switch (key) {
      case 'cgun':
        return ozet?.cgun ?? ng
      case 'gun_maasi_kesintisi':
        return maasGorebilir && ozet?.gun_maasi_kesintisi ? `−${fmt(ozet.gun_maasi_kesintisi)}` : ''
      case 'yillik_izin_gun':
        return ozet?.yillik_izin_gun || ''
      case 'raporlu_gun':
        return ozet?.raporlu_gun || ''
      case 'izin_saat':
        return ozet?.izin_saat || ''
      case 'izin_tl':
        return maasGorebilir && ozet?.izin_tl ? `−${fmt(ozet.izin_tl)}` : ''
      case 'fm_saat':
        return ozet?.fm_saat || ''
      case 'fm_tl':
        return maasGorebilir && ozet?.fm_tl ? fmt(ozet.fm_tl) : ''
    }
  }

  return (
    <Box
      sx={{
        // Kullanıcı geri bildirimi (2026-07-04): "temmuz kaç gün, günler eksik
        // görünüyor" — veri doğruydu (31 gün DOM'da vardı) ama bu kutunun kendi
        // yatay kaydırma çubuğu onlarca satırın ALTINDA kaldığı için hiç fark
        // edilmiyordu. Yükseklik sınırlanıp başlık sticky yapılınca kaydırma
        // çubuğu her zaman görünür bir yerde (kutunun altında) duruyor.
        overflow: 'auto',
        maxHeight: 'calc(100vh - 192px)',
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 2,
      }}
    >
      <Table size="small" sx={{ borderCollapse: 'separate', borderSpacing: 0 }}>
        <TableHead>
          <TableRow>
            <TableCell
              sx={{
                position: 'sticky',
                left: 0,
                top: 0,
                zIndex: 4,
                bgcolor: 'secondary.main',
                color: 'white',
                minWidth: 200,
                fontWeight: 700,
                borderRight: '1px solid',
                borderColor: GRID_CIZGI_RENGI,
                boxShadow: SOL_SABIT_GOLGE,
              }}
            >
              {TR_AYLAR[donem.ay - 1]} {donem.yil} — Personel
            </TableCell>
            {gunler.map((g) => {
              const gunAdiIndex = new Date(donem.yil, donem.ay - 1, g).getDay()
              // Hafta tatili günü artık kişiye göre değişebildiği için (bkz. haftaTatiliMi)
              // header'da yalnızca RESMİ TATİL vurgusu kalıyor — o herkes için aynı.
              // Hangi günlerin hafta tatili olduğu, aşağıda her personel satırında ayrı gösteriliyor.
              const tatil = tatilSet.has(ymd(donem.yil, donem.ay, g))
              return (
                <TableCell
                  key={g}
                  align="center"
                  sx={{
                    position: 'sticky',
                    top: 0,
                    zIndex: 1,
                    bgcolor: tatil ? TATIL_BASLIK_RENGI : 'secondary.main',
                    color: tatil ? 'error.main' : 'white',
                    fontSize: 11,
                    p: 0.5,
                    minWidth: 34,
                    borderRight: '1px solid',
                    borderColor: GRID_CIZGI_RENGI,
                  }}
                >
                  <div>{g}</div>
                  <div style={{ opacity: 0.8 }}>{TR_GUN_KISA[gunAdiIndex]}</div>
                </TableCell>
              )
            })}
            {OZET_KOLONLARI.map((k) => (
              <TableCell
                key={k.key}
                align="center"
                sx={{
                  position: 'sticky',
                  top: 0,
                  zIndex: 1,
                  bgcolor: 'secondary.main',
                  color: 'white',
                  fontSize: 11,
                  minWidth: SUM_KOLON_GENISLIK,
                  borderRight: '1px solid',
                  borderColor: GRID_CIZGI_RENGI,
                }}
              >
                {k.etiket}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {gorunenPersonel.map((p) => {
            const ozet = ozetMap.get(p.id)
            const tip = tipMap.get(p.calisma_tipi_id)
            const haftaTatiliGunleri = tip?.hafta_tatili_gunleri ?? VARSAYILAN_HAFTA_TATILI
            return (
              <TableRow key={p.id} hover>
                <TableCell
                  sx={{
                    position: 'sticky',
                    left: 0,
                    zIndex: 2,
                    bgcolor: 'background.paper',
                    borderRight: '1px solid',
                    borderBottom: '1px solid',
                    borderColor: GRID_CIZGI_RENGI,
                    boxShadow: SOL_SABIT_GOLGE,
                  }}
                >
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {p.ad_soyad}
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    {maasGorebilir && p.maas != null && (
                      <Typography variant="caption" color="text.secondary">
                        {fmt(p.maas)} ₺ ·
                      </Typography>
                    )}
                    {ngDuzenlenenId === p.id ? (
                      <TextField
                        autoFocus
                        type="number"
                        size="small"
                        variant="standard"
                        sx={{ width: 48 }}
                        value={ngGirisDegeri}
                        onChange={(e) => setNgGirisDegeri(e.target.value)}
                        onBlur={() => setNgDuzenlenenId(null)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            const deger = ngGirisDegeri.trim()
                            onNgAyarla(p.id, deger === '' ? null : parseInt(deger, 10))
                            setNgDuzenlenenId(null)
                          } else if (e.key === 'Escape') {
                            setNgDuzenlenenId(null)
                          }
                        }}
                      />
                    ) : (
                      <Typography variant="caption" color="text.secondary">
                        {ozet?.ng ?? p.ng} gün
                      </Typography>
                    )}
                    {personelYonetebilir && ngDuzenlenenId !== p.id && (
                      <IconButton
                        size="small"
                        sx={{ p: 0.25 }}
                        title="Bu ay için N.G istisnası gir (boş bırakırsan takvim varsayılanına döner)"
                        onClick={() => {
                          setNgDuzenlenenId(p.id)
                          setNgGirisDegeri(String(ozet?.ng ?? p.ng))
                        }}
                      >
                        <EditIcon sx={{ fontSize: 14 }} />
                      </IconButton>
                    )}
                  </Box>
                </TableCell>
                {gunler.map((g) => {
                  const tarih = ymd(donem.yil, donem.ay, g)
                  const giris = girisMap.get(`${p.id}|${tarih}`)
                  const pazar = haftaTatiliMi(haftaTatiliGunleri, donem.yil, donem.ay, g)
                  const tatil = tatilSet.has(tarih)
                  const devreDisi = !gunCalisiyorMu(p, tarih)
                  return (
                    <DayCell
                      key={g}
                      tatilMi={tatil}
                      pazarMi={pazar}
                      devreDisiMi={devreDisi}
                      gunlukSaat={tip?.gunluk_saat}
                      giris={giris}
                      onSolTik={() => onGunToggle(p.id, tarih, giris)}
                      onSagTik={(e) => {
                        setPopoverAnchor(e.currentTarget)
                        setAktifHucre({ personelId: p.id, calismaTipiId: p.calisma_tipi_id, tarih, ad: p.ad_soyad, gun: g })
                      }}
                    />
                  )
                })}
                {OZET_KOLONLARI.map((k) => (
                  <TableCell
                    key={k.key}
                    align="center"
                    sx={{
                      bgcolor: 'background.paper',
                      color:
                        k.key === 'izin_tl' || k.key === 'gun_maasi_kesintisi'
                          ? 'error.main'
                          : k.key === 'fm_tl'
                            ? 'info.main'
                            : undefined,
                      borderRight: '1px solid',
                      borderColor: GRID_CIZGI_RENGI,
                    }}
                  >
                    {ozetHucreIcerik(ozet, k.key, p.ng)}
                  </TableCell>
                ))}
              </TableRow>
            )
          })}
        </TableBody>
      </Table>

      {aktifHucre && (
        <EntryPopover
          anchorEl={popoverAnchor}
          onClose={() => {
            setPopoverAnchor(null)
            setAktifHucre(null)
          }}
          personelAdi={aktifHucre.ad}
          tarihEtiketi={`${aktifHucre.gun} ${TR_AYLAR[donem.ay - 1].charAt(0)}${TR_AYLAR[donem.ay - 1].slice(1).toLowerCase()}`}
          x2={
            haftaTatiliMi(
              tipMap.get(aktifHucre.calismaTipiId)?.hafta_tatili_gunleri ?? VARSAYILAN_HAFTA_TATILI,
              donem.yil,
              donem.ay,
              aktifHucre.gun,
            ) || tatilSet.has(ymd(donem.yil, donem.ay, aktifHucre.gun))
          }
          gunlukSaat={tipMap.get(aktifHucre.calismaTipiId)?.gunluk_saat ?? VARSAYILAN_GUNLUK_SAAT}
          mevcutGiris={girisMap.get(`${aktifHucre.personelId}|${aktifHucre.tarih}`)}
          onKaydet={(gunDurumu, izinSaat, fmSaat) =>
            onGunKaydet(aktifHucre.personelId, aktifHucre.tarih, gunDurumu, izinSaat, fmSaat)
          }
          onTemizle={() => onGunTemizle(aktifHucre.personelId, aktifHucre.tarih)}
        />
      )}
    </Box>
  )
}
