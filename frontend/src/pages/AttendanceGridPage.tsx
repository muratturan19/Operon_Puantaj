import { useCallback, useEffect, useMemo, useState } from 'react'
import { Alert, Box, Button, MenuItem, Select, Stack, Typography, type SelectChangeEvent } from '@mui/material'
import {
  donemGetirVeyaOlustur,
  donemiTemizle,
  gunGuncelle,
  listeleDonemler,
  listeleGirisler,
  listeleTatiller,
  ozet,
  personelDonemNgAyarla,
  tatilEkle,
  tatilSil,
} from '../services/attendanceService'
import { listeleCalismaTipleri, listelePersonel } from '../services/personelService'
import { excelDisaAktar, listeleMappingSablonlari } from '../services/excelService'
import { useAuth } from '../context/AuthContext'
import { PuantajGrid } from '../components/attendance/PuantajGrid'
import { HolidaysDialog } from '../components/attendance/HolidaysDialog'
import { TR_AYLAR } from '../utils/date'
import type { CalismaTipi, Donem, GunDurumu, Personel, PersonelOzet, PuantajGirisi, Tatil } from '../services/types'

function secimAnahtari(yil: number, ay: number): string {
  return `${yil}-${ay}`
}

export function AttendanceGridPage() {
  const { izniVar } = useAuth()
  const [donemler, setDonemler] = useState<Donem[]>([])
  // Seçim, gerçekte var olan bir Donem'e değil (yıl, ay) çiftine bağlı —
  // kullanıcı geri bildirimi (2026-07-04): dönem seçicide henüz Excel'i içe
  // aktarılmamış aylar da (ör. temmuz sonuna erken yıllık izin girmek için)
  // seçilebilir olmalı. Seçildiğinde dönem yoksa sessizce oluşturulur.
  const [secim, setSecim] = useState<{ yil: number; ay: number } | null>(null)
  const [donemId, setDonemId] = useState<number | ''>('')
  const [personelListesi, setPersonelListesi] = useState<Personel[]>([])
  const [tipler, setTipler] = useState<CalismaTipi[]>([])
  const [girisler, setGirisler] = useState<PuantajGirisi[]>([])
  const [ozetListesi, setOzetListesi] = useState<PersonelOzet[]>([])
  const [tatiller, setTatiller] = useState<Tatil[]>([])
  const [tatilDialogAcik, setTatilDialogAcik] = useState(false)
  const [mappingSablonId, setMappingSablonId] = useState<number | null>(null)

  useEffect(() => {
    listeleMappingSablonlari().then((s) => setMappingSablonId(s[0]?.id ?? null))
  }, [])

  useEffect(() => {
    listeleDonemler().then((liste) => {
      setDonemler(liste)
      const bugun = new Date()
      // Varsayılan: bugünün ayı dönemler arasında varsa o seçilir (kullanıcı
      // muhtemelen orada çalışıyordur); yoksa en son dönem. Bu sayede "temmuz
      // sonuna erken izin gir" diye bir kerelik ileri bakmak, sonraki girişte
      // varsayılan görünümü temmuza kaydırmaz.
      const buAy = liste.find((d) => d.yil === bugun.getFullYear() && d.ay === bugun.getMonth() + 1)
      const son = liste[liste.length - 1]
      const hedef = buAy ?? son
      setSecim(hedef ? { yil: hedef.yil, ay: hedef.ay } : { yil: bugun.getFullYear(), ay: bugun.getMonth() + 1 })
    })
    listelePersonel().then(setPersonelListesi)
    listeleTatiller().then(setTatiller)
    listeleCalismaTipleri().then(setTipler)
  }, [])

  // Seçilen (yıl, ay) için var olan dönemi bul; yoksa get-or-create ile oluştur.
  useEffect(() => {
    if (!secim) return
    const mevcut = donemler.find((d) => d.yil === secim.yil && d.ay === secim.ay)
    if (mevcut) {
      setDonemId(mevcut.id)
      return
    }
    let iptal = false
    donemGetirVeyaOlustur(secim.yil, secim.ay).then((yeni) => {
      if (iptal) return
      setDonemler((prev) => (prev.some((d) => d.id === yeni.id) ? prev : [...prev, yeni]))
      setDonemId(yeni.id)
    })
    return () => {
      iptal = true
    }
  }, [secim, donemler])

  const secenekler = useMemo(() => {
    const bugun = new Date()
    const yillar = new Set(donemler.map((d) => d.yil))
    yillar.add(bugun.getFullYear())
    return [...yillar].sort((a, b) => a - b).flatMap((yil) =>
      Array.from({ length: 12 }, (_, i) => {
        const ay = i + 1
        const varMi = donemler.some((d) => d.yil === yil && d.ay === ay)
        return { yil, ay, varMi }
      }),
    )
  }, [donemler])

  const verileriYenile = useCallback(async () => {
    if (!donemId) return
    const [g, o] = await Promise.all([listeleGirisler(donemId), ozet(donemId)])
    setGirisler(g)
    setOzetListesi(o)
  }, [donemId])

  useEffect(() => {
    verileriYenile()
  }, [verileriYenile])

  const secilenDonem = donemler.find((d) => d.id === donemId)

  async function onGunToggle(personelId: number, tarih: string, mevcut: PuantajGirisi | undefined) {
    // Sol tık: devamsızlık toggle — devamsız işaretlenirse izin/FM sıfırlanır (Puantaj.html davranışı)
    const yeniDevamsiz = mevcut?.gun_durumu !== 'devamsiz'
    await gunGuncelle(personelId, tarih, {
      gun_durumu: yeniDevamsiz ? 'devamsiz' : null,
      izin_saat: yeniDevamsiz ? 0 : mevcut?.izin_saat || 0,
      fm_saat: yeniDevamsiz ? 0 : mevcut?.fm_saat || 0,
    })
    verileriYenile()
  }

  async function onGunKaydet(
    personelId: number,
    tarih: string,
    gunDurumu: GunDurumu,
    izinSaat: number,
    fmSaat: number,
  ) {
    await gunGuncelle(personelId, tarih, { gun_durumu: gunDurumu, izin_saat: izinSaat, fm_saat: fmSaat })
    verileriYenile()
  }

  async function onGunTemizle(personelId: number, tarih: string) {
    await gunGuncelle(personelId, tarih, { gun_durumu: null, izin_saat: 0, fm_saat: 0 })
    verileriYenile()
  }

  async function onNgAyarla(personelId: number, ng: number | null) {
    if (!donemId) return
    await personelDonemNgAyarla(personelId, donemId, ng)
    verileriYenile()
  }

  if (!secim) {
    return <Typography>Yükleniyor…</Typography>
  }
  if (!secilenDonem) {
    return <Typography>Dönem hazırlanıyor…</Typography>
  }

  return (
    <Box>
      <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 3 }}>
        <Select
          size="small"
          value={secimAnahtari(secim.yil, secim.ay)}
          onChange={(e: SelectChangeEvent<string>) => {
            const [yil, ay] = e.target.value.split('-').map(Number)
            setSecim({ yil, ay })
          }}
        >
          {secenekler.map(({ yil, ay, varMi }) => (
            <MenuItem key={secimAnahtari(yil, ay)} value={secimAnahtari(yil, ay)}>
              {TR_AYLAR[ay - 1]} {yil}
              {!varMi && ' (yeni)'}
            </MenuItem>
          ))}
        </Select>
        <Button variant="outlined" size="small" onClick={() => setTatilDialogAcik(true)}>
          Tatiller
        </Button>
        {mappingSablonId && izniVar('excel_disa_aktarabilir') && izniVar('gorebilir_maas_tutari') && (
          <Button
            variant="outlined"
            size="small"
            onClick={() => excelDisaAktar(mappingSablonId, secilenDonem.id)}
          >
            Excel'e Aktar
          </Button>
        )}
        {izniVar('donem_temizleyebilir') && (
          <Button
            variant="outlined"
            color="error"
            size="small"
            onClick={async () => {
              if (!confirm(`${TR_AYLAR[secilenDonem.ay - 1]} ${secilenDonem.yil} ayındaki tüm işaretlemeler silinsin mi?`)) return
              await donemiTemizle(secilenDonem.id)
              verileriYenile()
            }}
          >
            Ayı Temizle
          </Button>
        )}
      </Stack>

      {!izniVar('audit_gorebilir') && (
        <Alert severity="info" variant="outlined" sx={{ mb: 2, py: 0 }}>
          Bu ekrandaki tüm işaretlemeler ve değişiklikler, kim tarafından ve ne zaman yapıldığı
          bilgisiyle birlikte kayıt altına alınmaktadır.
        </Alert>
      )}

      <PuantajGrid
        donem={secilenDonem}
        personelListesi={personelListesi}
        tipler={tipler}
        girisler={girisler}
        ozetListesi={ozetListesi}
        tatiller={tatiller}
        maasGorebilir={izniVar('gorebilir_maas_tutari')}
        personelYonetebilir={izniVar('personel_yonetebilir')}
        onGunToggle={onGunToggle}
        onGunKaydet={onGunKaydet}
        onGunTemizle={onGunTemizle}
        onNgAyarla={onNgAyarla}
      />

      <HolidaysDialog
        acik={tatilDialogAcik}
        onKapat={() => setTatilDialogAcik(false)}
        tatiller={tatiller}
        onEkle={async (tarih) => {
          await tatilEkle(tarih)
          listeleTatiller().then(setTatiller)
        }}
        onSil={async (id) => {
          await tatilSil(id)
          listeleTatiller().then(setTatiller)
        }}
      />
    </Box>
  )
}
