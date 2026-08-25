import { useEffect, useState, type ReactNode } from 'react'
import { Link as RouterLink, useLocation } from 'react-router-dom'
import {
  Alert,
  AppBar,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  TextField,
  Toolbar,
  Tooltip,
  Typography,
} from '@mui/material'
import { useAuth } from '../context/AuthContext'
import { AUTH_MODE } from '../config/env'
import { FRONTEND_SURUM } from '../config/surum'
import { parolaDegistir } from '../services/usersService'
import { surumGetir, type SurumBilgisi } from '../services/surumService'

interface NavItem {
  to: string
  etiket: string
  gerekliIzin?: string
  gizliSaas?: boolean
}

const NAV_ITEMS: NavItem[] = [
  { to: '/', etiket: 'Puantaj' },
  { to: '/personel', etiket: 'Personel', gerekliIzin: 'personel_yonetebilir' },
  { to: '/calisma-tipleri', etiket: 'Çalışma Tipleri', gerekliIzin: 'calisma_tipi_yonetebilir' },
  // Kullanıcılar/Roller SaaS modda gizli — atama Portal'dan yapılır (CLAUDE.md §8.8 madde 4).
  { to: '/kullanicilar', etiket: 'Kullanıcılar', gerekliIzin: 'kullanici_yonetebilir', gizliSaas: true },
  { to: '/ayarlar', etiket: 'Excel Aktarım', gerekliIzin: 'excel_ice_aktarabilir' },
  { to: '/sirket-ayarlari', etiket: 'Şirket Ayarları', gerekliIzin: 'sirket_ayarlarini_yonetebilir' },
  { to: '/guvenlik', etiket: 'Güvenlik', gerekliIzin: 'audit_gorebilir' },
]

export function AppLayout({ children }: { children: ReactNode }) {
  const { user, cikisYap, izniVar } = useAuth()
  const location = useLocation()
  const [sifreDialogAcik, setSifreDialogAcik] = useState(false)
  const [yeniSifre, setYeniSifre] = useState('')
  const [yeniSifreTekrar, setYeniSifreTekrar] = useState('')
  const [hata, setHata] = useState<string | null>(null)
  const [mesaj, setMesaj] = useState<string | null>(null)
  const [sunucuSurumu, setSunucuSurumu] = useState<SurumBilgisi | null>(null)

  useEffect(() => {
    surumGetir().then(setSunucuSurumu).catch(() => setSunucuSurumu(null))
  }, [])

  // Sunucu yeni sürüme geçtiği halde tarayıcıda önbellekten eski paket açıksa
  // kullanıcı düzeltilmiş bir hatayı görmeye devam eder ve bunu anlamasının
  // hiçbir yolu yoktur — rozet bu durumda uyarıya döner.
  const eskiPaket = sunucuSurumu !== null && sunucuSurumu.surum !== FRONTEND_SURUM

  function dialoguKapat() {
    setSifreDialogAcik(false)
    setYeniSifre('')
    setYeniSifreTekrar('')
    setHata(null)
  }

  async function sifreyiKaydet() {
    if (!user) return
    if (yeniSifre.length < 6) {
      setHata('Şifre en az 6 karakter olmalı')
      return
    }
    if (yeniSifre !== yeniSifreTekrar) {
      setHata('Şifreler eşleşmiyor')
      return
    }
    setHata(null)
    try {
      await parolaDegistir(user.id, yeniSifre)
      dialoguKapat()
      setMesaj('Şifreniz güncellendi')
    } catch {
      setHata('Şifre güncellenemedi, tekrar deneyin')
    }
  }

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <AppBar position="static" sx={{ bgcolor: 'secondary.main' }} elevation={0}>
        <Toolbar sx={{ gap: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>
            Operon <Box component="span" sx={{ color: 'primary.main' }}>Puantaj</Box>
          </Typography>
          <Tooltip
            title={
              eskiPaket
                ? `Tarayıcınızda v${FRONTEND_SURUM} yüklü, sunucuda v${sunucuSurumu?.surum} çalışıyor — sayfayı yenileyin (Ctrl+F5).`
                : sunucuSurumu
                  ? `${sunucuSurumu.ad} — ${sunucuSurumu.tarih}`
                  : 'Sürüm bilgisi alınamadı'
            }
          >
            <Chip
              size="small"
              label={eskiPaket ? `v${FRONTEND_SURUM} — yenileyin` : `v${sunucuSurumu?.surum ?? FRONTEND_SURUM}`}
              color={eskiPaket ? 'warning' : 'default'}
              variant={eskiPaket ? 'filled' : 'outlined'}
              sx={{ color: 'white', borderColor: 'rgba(255,255,255,0.4)' }}
            />
          </Tooltip>
          <Stack direction="row" spacing={1} sx={{ flexGrow: 1 }}>
            {NAV_ITEMS.filter(
              (item) =>
                (!item.gerekliIzin || izniVar(item.gerekliIzin)) && !(item.gizliSaas && AUTH_MODE === 'saas'),
            ).map((item) => (
              <Button
                key={item.to}
                component={RouterLink}
                to={item.to}
                sx={{
                  color: 'white',
                  opacity: location.pathname === item.to ? 1 : 0.75,
                  borderBottom: location.pathname === item.to ? '2px solid' : '2px solid transparent',
                  borderColor: 'primary.main',
                  borderRadius: 0,
                }}
              >
                {item.etiket}
              </Button>
            ))}
          </Stack>
          <Typography variant="body2" sx={{ opacity: 0.8 }}>
            {user?.ad_soyad}
          </Typography>
          <Button color="inherit" size="small" onClick={() => setSifreDialogAcik(true)}>
            Şifremi Değiştir
          </Button>
          <Button color="inherit" onClick={cikisYap} size="small">
            Çıkış
          </Button>
        </Toolbar>
      </AppBar>
      <Box sx={{ p: { xs: 2, md: 4 } }}>
        {mesaj && (
          <Alert severity="success" onClose={() => setMesaj(null)} sx={{ mb: 2 }}>
            {mesaj}
          </Alert>
        )}
        {children}
      </Box>

      <Dialog open={sifreDialogAcik} onClose={dialoguKapat}>
        <DialogTitle>Şifremi Değiştir</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1, minWidth: 320 }}>
            {hata && <Alert severity="error">{hata}</Alert>}
            <TextField
              autoFocus
              label="Yeni Şifre"
              type="password"
              size="small"
              fullWidth
              value={yeniSifre}
              onChange={(e) => setYeniSifre(e.target.value)}
            />
            <TextField
              label="Yeni Şifre (Tekrar)"
              type="password"
              size="small"
              fullWidth
              value={yeniSifreTekrar}
              onChange={(e) => setYeniSifreTekrar(e.target.value)}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={dialoguKapat}>İptal</Button>
          <Button variant="contained" disabled={!yeniSifre || !yeniSifreTekrar} onClick={sifreyiKaydet}>
            Kaydet
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
