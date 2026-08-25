import { useEffect, useState } from 'react'
import {
  Alert,
  Button,
  FormControl,
  FormControlLabel,
  Paper,
  Radio,
  RadioGroup,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { sirketGetir, sirketGuncelle, type RaporluPolitikasi } from '../services/sirketService'

const POLITIKA_ETIKETLERI: Record<RaporluPolitikasi, { baslik: string; aciklama: string }> = {
  tam_ode: { baslik: 'Tam Öde', aciklama: 'Raporlu günler maaştan hiç düşmez (Yıllık İzin gibi).' },
  hic_odeme: { baslik: 'Hiç Ödeme', aciklama: 'Raporlu günlerin tamamı maaştan düşer (varsayılan).' },
  n_gun_esigi: {
    baslik: 'N Gün Eşiği',
    aciklama: 'Her ardışık rapor bloğunun ilk N günü ödenir, kalanı maaştan düşer.',
  },
}

export function CompanySettingsPage() {
  const [politika, setPolitika] = useState<RaporluPolitikasi>('hic_odeme')
  const [esikGun, setEsikGun] = useState(0)
  const [mesaj, setMesaj] = useState<string | null>(null)
  const [hata, setHata] = useState<string | null>(null)
  const [kaydediliyor, setKaydediliyor] = useState(false)

  useEffect(() => {
    sirketGetir().then((s) => {
      setPolitika(s.raporlu_politikasi)
      setEsikGun(s.raporlu_esik_gun)
    })
  }, [])

  async function kaydet() {
    setMesaj(null)
    setHata(null)
    setKaydediliyor(true)
    try {
      await sirketGuncelle({
        raporlu_politikasi: politika,
        raporlu_esik_gun: politika === 'n_gun_esigi' ? esikGun : 0,
      })
      setMesaj('Kaydedildi')
    } catch {
      setHata('Kaydetme başarısız oldu')
    } finally {
      setKaydediliyor(false)
    }
  }

  return (
    <Stack spacing={3} sx={{ maxWidth: 640 }}>
      <Typography variant="h5" sx={{ fontWeight: 700 }}>
        Şirket Ayarları
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 640 }}>
        Raporlu (sağlık raporu) günlerinin maaşa nasıl yansıyacağını şirket geneli olarak
        buradan belirleyin.
      </Typography>

      {mesaj && <Alert severity="success">{mesaj}</Alert>}
      {hata && <Alert severity="error">{hata}</Alert>}

      <Paper variant="outlined" sx={{ p: 3 }}>
        <Typography variant="subtitle2" sx={{ mb: 2 }}>
          Raporlu Ödeme Politikası
        </Typography>
        <FormControl>
          <RadioGroup value={politika} onChange={(e) => setPolitika(e.target.value as RaporluPolitikasi)}>
            {(Object.keys(POLITIKA_ETIKETLERI) as RaporluPolitikasi[]).map((p) => (
              <FormControlLabel
                key={p}
                value={p}
                control={<Radio />}
                label={
                  <Stack>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {POLITIKA_ETIKETLERI[p].baslik}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {POLITIKA_ETIKETLERI[p].aciklama}
                    </Typography>
                  </Stack>
                }
                sx={{ mb: 1.5, alignItems: 'flex-start' }}
              />
            ))}
          </RadioGroup>
        </FormControl>

        {politika === 'n_gun_esigi' && (
          <TextField
            label="Eşik Gün Sayısı"
            type="number"
            size="small"
            value={esikGun}
            onChange={(e) => setEsikGun(Math.max(0, Number(e.target.value)))}
            sx={{ mt: 1, maxWidth: 200 }}
          />
        )}

        <Stack direction="row" sx={{ mt: 3 }}>
          <Button variant="contained" onClick={kaydet} disabled={kaydediliyor}>
            Kaydet
          </Button>
        </Stack>
      </Paper>
    </Stack>
  )
}
