import { Box } from '@mui/material'
import type { PuantajGirisi } from '../../services/types'
import { GRID_CIZGI_RENGI, PAZAR_TATIL_HUCRE_RENGI } from '../../utils/date'
import { VARSAYILAN_GUNLUK_SAAT, saatMetni, yarimGunMu } from '../../utils/saat'

interface Props {
  tatilMi: boolean
  pazarMi: boolean
  devreDisiMi?: boolean // personel bu gün henüz işe girmemiş / zaten ayrılmış
  gunlukSaat?: number
  giris: PuantajGirisi | undefined
  onSolTik: () => void
  onSagTik: (e: React.MouseEvent<HTMLElement>) => void
}

export function DayCell({ tatilMi, pazarMi, devreDisiMi, gunlukSaat, giris, onSolTik, onSagTik }: Props) {
  const gunDurumu = giris?.gun_durumu ?? null
  const izin = giris?.izin_saat || 0
  const fm = giris?.fm_saat || 0
  // 34px'lik hücreye "3,75i" sığmıyor — yarım gün kısaca "½" gösterilir.
  const izinMetni = yarimGunMu(izin, gunlukSaat ?? VARSAYILAN_GUNLUK_SAAT) ? '½' : saatMetni(izin)

  let bgcolor: string = tatilMi || pazarMi ? PAZAR_TATIL_HUCRE_RENGI : 'transparent'
  let renk: string | undefined
  let icerik = ''

  if (gunDurumu === 'devamsiz') {
    bgcolor = 'error.main'
    renk = 'white'
    icerik = '×'
  } else if (gunDurumu === 'yillik_izin') {
    bgcolor = 'success.main'
    renk = 'white'
    icerik = 'Yİ'
  } else if (gunDurumu === 'raporlu') {
    bgcolor = 'warning.main'
    renk = 'white'
    icerik = 'R'
  } else if (izin && fm) {
    bgcolor = 'secondary.light'
    renk = 'white'
    icerik = `${izinMetni}i/${saatMetni(fm)}`
  } else if (izin) {
    bgcolor = 'error.light'
    renk = 'white'
    icerik = `${izinMetni}i`
  } else if (fm) {
    bgcolor = 'info.light'
    renk = 'white'
    icerik = `+${saatMetni(fm)}`
  }

  return (
    <Box
      component="td"
      onClick={devreDisiMi ? undefined : onSolTik}
      onContextMenu={(e: React.MouseEvent<HTMLElement>) => {
        e.preventDefault()
        if (!devreDisiMi) onSagTik(e)
      }}
      title={
        devreDisiMi
          ? 'Bu tarihte henüz işe girmemiş / işten ayrılmış'
          : izin
            ? `${saatMetni(izin)} saat izin${fm ? ` · ${saatMetni(fm)} saat FM` : ''}`
            : `Sol tık: gelmedi · Sağ tık: izin/FM/yarım gün/yıllık izin/raporlu${pazarMi || tatilMi ? ' (bu gün FM ×2)' : ''}`
      }
      sx={{
        width: 34,
        minWidth: 34,
        height: 32,
        textAlign: 'center',
        verticalAlign: 'middle',
        fontSize: 12,
        fontWeight: 700,
        cursor: devreDisiMi ? 'not-allowed' : 'pointer',
        userSelect: 'none',
        bgcolor: devreDisiMi ? 'action.disabledBackground' : bgcolor,
        color: renk,
        opacity: devreDisiMi ? 0.5 : 1,
        borderRight: '1px solid',
        borderBottom: '1px solid',
        borderColor: GRID_CIZGI_RENGI,
        '&:hover': devreDisiMi ? undefined : { outline: '2px solid', outlineColor: 'primary.main', outlineOffset: -2 },
      }}
    >
      {icerik}
    </Box>
  )
}
