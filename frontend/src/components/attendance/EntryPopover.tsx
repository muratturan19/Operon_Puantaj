import { useState } from 'react'
import {
  Box,
  Button,
  Chip,
  Popover,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material'
import type { GunDurumu, PuantajGirisi } from '../../services/types'
import { VARSAYILAN_GUNLUK_SAAT, saatMetni, yarimGunSaati } from '../../utils/saat'

interface Props {
  anchorEl: HTMLElement | null
  onClose: () => void
  personelAdi: string
  tarihEtiketi: string
  x2: boolean
  gunlukSaat: number
  mevcutGiris: PuantajGirisi | undefined
  onKaydet: (gunDurumu: GunDurumu, izinSaat: number, fmSaat: number) => void
  onTemizle: () => void
}

// "devamsiz" burada YOK — o sol tıkla yönetiliyor (mevcut davranış korunuyor).
const TAM_GUN_SECENEKLERI: { deger: Exclude<GunDurumu, 'devamsiz' | null>; etiket: string }[] = [
  { deger: 'yillik_izin', etiket: 'Yıllık İzin' },
  { deger: 'raporlu', etiket: 'Raporlu' },
]

export function EntryPopover({
  anchorEl,
  onClose,
  personelAdi,
  tarihEtiketi,
  x2,
  gunlukSaat,
  mevcutGiris,
  onKaydet,
  onTemizle,
}: Props) {
  const baslangicTamGun =
    mevcutGiris?.gun_durumu === 'yillik_izin' || mevcutGiris?.gun_durumu === 'raporlu'
      ? mevcutGiris.gun_durumu
      : null
  const [tamGun, setTamGun] = useState<'yillik_izin' | 'raporlu' | null>(baslangicTamGun)
  const [izin, setIzin] = useState(String(mevcutGiris?.izin_saat || ''))
  const [fm, setFm] = useState(String(mevcutGiris?.fm_saat || ''))

  const acik = Boolean(anchorEl)
  const saatlikDevreDisi = tamGun !== null
  const yarimGun = yarimGunSaati(gunlukSaat || VARSAYILAN_GUNLUK_SAAT)

  return (
    <Popover
      open={acik}
      anchorEl={anchorEl}
      onClose={onClose}
      anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
      transformOrigin={{ vertical: 'top', horizontal: 'left' }}
    >
      <Box sx={{ p: 2, width: 280 }}>
        <Typography variant="subtitle2" sx={{ mb: 1.5, fontWeight: 700 }}>
          {personelAdi} — {tarihEtiketi}
        </Typography>
        <Stack spacing={1.5}>
          <ToggleButtonGroup
            size="small"
            exclusive
            fullWidth
            value={tamGun}
            onChange={(_e, yeniDeger) => setTamGun(yeniDeger)}
          >
            {TAM_GUN_SECENEKLERI.map((s) => (
              <ToggleButton key={s.deger} value={s.deger}>
                {s.etiket}
              </ToggleButton>
            ))}
          </ToggleButtonGroup>

          <Stack direction="row" spacing={1} alignItems="flex-start">
            <TextField
              label="İzin (saat)"
              type="number"
              size="small"
              value={izin}
              disabled={saatlikDevreDisi}
              // step 0,25 — yarım gün 3,75 saat, 0,5'lik adımda geçersiz sayılırdı
              inputProps={{ min: 0, step: 0.25 }}
              onChange={(e) => setIzin(e.target.value)}
              fullWidth
            />
            <Button
              size="small"
              variant={parseFloat(izin) === yarimGun ? 'contained' : 'outlined'}
              disabled={saatlikDevreDisi}
              onClick={() => setIzin(String(yarimGun))}
              sx={{ whiteSpace: 'nowrap', mt: 0.25, minWidth: 104 }}
            >
              Yarım gün
            </Button>
          </Stack>
          <Typography variant="caption" color="text.secondary" sx={{ mt: -0.5 }}>
            Yarım gün = {saatMetni(yarimGun)} saat (günlük {saatMetni(gunlukSaat || VARSAYILAN_GUNLUK_SAAT)} saat)
          </Typography>
          <TextField
            label="Fazla mesai (saat)"
            type="number"
            size="small"
            value={fm}
            disabled={saatlikDevreDisi}
            inputProps={{ min: 0, step: 0.25 }}
            onChange={(e) => setFm(e.target.value)}
            fullWidth
          />
          {!saatlikDevreDisi && (
            <Chip
              size="small"
              label={`FM oranı: ×${x2 ? '2 (pazar/tatil)' : '1,5'}`}
              sx={{ alignSelf: 'flex-start' }}
            />
          )}
          {saatlikDevreDisi && (
            <Typography variant="caption" color="text.secondary">
              Tam gün statüsü seçildi — izin/FM saatleri bu günde geçersiz.
            </Typography>
          )}

          <Stack direction="row" spacing={1} justifyContent="flex-end">
            <Button
              size="small"
              onClick={() => {
                onTemizle()
                onClose()
              }}
            >
              Temizle
            </Button>
            <Button
              size="small"
              variant="contained"
              onClick={() => {
                if (tamGun) {
                  onKaydet(tamGun, 0, 0)
                } else {
                  onKaydet(null, parseFloat(izin) || 0, parseFloat(fm) || 0)
                }
                onClose()
              }}
            >
              Kaydet
            </Button>
          </Stack>
        </Stack>
      </Box>
    </Popover>
  )
}
