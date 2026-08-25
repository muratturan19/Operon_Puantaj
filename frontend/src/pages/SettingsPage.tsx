import { useEffect, useRef, useState } from 'react'
import { Alert, Button, MenuItem, Paper, Select, Stack, Typography } from '@mui/material'
import { excelDisaAktar, excelIceAktar, listeleMappingSablonlari, type MappingTemplate } from '../services/excelService'
import { listeleDonemler } from '../services/attendanceService'
import { TR_AYLAR } from '../utils/date'
import type { Donem } from '../services/types'

export function SettingsPage() {
  const [sablonlar, setSablonlar] = useState<MappingTemplate[]>([])
  const [sablonId, setSablonId] = useState<number | ''>('')
  const [donemler, setDonemler] = useState<Donem[]>([])
  const [donemId, setDonemId] = useState<number | ''>('')
  const [mesaj, setMesaj] = useState<string | null>(null)
  const [hata, setHata] = useState<string | null>(null)
  const dosyaInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    listeleMappingSablonlari().then((s) => {
      setSablonlar(s)
      if (s.length > 0) setSablonId(s[0].id)
    })
    listeleDonemler().then(setDonemler)
  }, [])

  async function onDosyaSecildi(e: React.ChangeEvent<HTMLInputElement>) {
    const dosya = e.target.files?.[0]
    if (!dosya || !sablonId) return
    setMesaj(null)
    setHata(null)
    try {
      const sonuc = await excelIceAktar(sablonId, dosya)
      setMesaj(
        `İçe aktarıldı — dönemler: ${sonuc.donemler_bulundu.join(', ')} | ${sonuc.personel_olusturulan} yeni, ${sonuc.personel_guncellenen} güncellenen personel`,
      )
      listeleDonemler().then(setDonemler)
    } catch {
      setHata('İçe aktarım başarısız oldu')
    } finally {
      if (dosyaInputRef.current) dosyaInputRef.current.value = ''
    }
  }

  return (
    <Stack spacing={3} sx={{ maxWidth: 640 }}>
      <Typography variant="h5" sx={{ fontWeight: 700 }}>
        Excel Aktarım
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 640 }}>
        Mevcut Excel dosyanızdaki personel listesini içe aktarın, ya da doldurduğunuz puantajı
        aynı Excel düzeninde geri dışa aktarın.
      </Typography>

      {mesaj && <Alert severity="success">{mesaj}</Alert>}
      {hata && <Alert severity="error">{hata}</Alert>}

      <Paper variant="outlined" sx={{ p: 3 }}>
        <Typography variant="subtitle2" sx={{ mb: 2 }}>
          İçe Aktar
        </Typography>
        <Stack spacing={2}>
          <Select size="small" value={sablonId} onChange={(e) => setSablonId(Number(e.target.value))} displayEmpty>
            <MenuItem value="" disabled>
              Mapping şablonu seç
            </MenuItem>
            {sablonlar.map((s) => (
              <MenuItem key={s.id} value={s.id}>
                {s.ad} (v{s.versiyon})
              </MenuItem>
            ))}
          </Select>
          <Button variant="contained" component="label" disabled={!sablonId}>
            Excel Dosyası Seç
            <input ref={dosyaInputRef} type="file" hidden accept=".xlsx" onChange={onDosyaSecildi} />
          </Button>
        </Stack>
      </Paper>

      <Paper variant="outlined" sx={{ p: 3 }}>
        <Typography variant="subtitle2" sx={{ mb: 2 }}>
          Dışa Aktar
        </Typography>
        <Stack direction="row" spacing={2}>
          <Select
            size="small"
            value={donemId}
            onChange={(e) => setDonemId(e.target.value === '' ? '' : Number(e.target.value))}
            displayEmpty
            sx={{ minWidth: 200 }}
          >
            <MenuItem value="">Tüm işaretli dönemler</MenuItem>
            {donemler.map((d) => (
              <MenuItem key={d.id} value={d.id}>
                {TR_AYLAR[d.ay - 1]} {d.yil}
              </MenuItem>
            ))}
          </Select>
          <Button
            variant="contained"
            disabled={!sablonId}
            onClick={async () => {
              setMesaj(null)
              setHata(null)
              const uyari = await excelDisaAktar(sablonId as number, donemId === '' ? undefined : donemId)
              if (uyari) setHata(uyari)
            }}
          >
            İndir
          </Button>
        </Stack>
      </Paper>
    </Stack>
  )
}
