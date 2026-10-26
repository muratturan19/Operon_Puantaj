import { useState, type FormEvent, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, Box, Button, Paper, Stack, TextField, Typography } from '@mui/material'
import { useAuth } from '../context/AuthContext'
import { AUTH_MODE, PORTAL_APPS_URL } from '../config/env'

/** Giriş kartının ortak çerçevesi — "Operon Puantaj" başlığı her iki modda aynı. */
function GirisKarti({ children }: { children: ReactNode }) {
  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        bgcolor: 'background.default',
      }}
    >
      <Paper elevation={0} sx={{ p: 4, width: 360, border: '1px solid', borderColor: 'divider' }}>
        <Typography variant="h5" sx={{ mb: 3, fontWeight: 700 }}>
          Operon <Box component="span" sx={{ color: 'primary.main' }}>Puantaj</Box>
        </Typography>
        {children}
      </Paper>
    </Box>
  )
}

/**
 * SaaS modda yerel kullanıcı adı/şifre girişi yoktur (`POST /api/auth/login` 404 döner);
 * oturum yalnız Portal SSO'dan gelir. Oturum yoksa ya da `/api/auth/me` başarısızsa
 * hiç çalışamayacak bir form göstermek yerine kullanıcı Portal'a yönlendirilir.
 * (26.10.2026: bakım sonrası bir kullanıcı bu forma kullanıcı adı/şifre yazıp
 * "Kullanıcı adı veya şifre hatalı" gördü.)
 */
function PortalGirisi() {
  return (
    <GirisKarti>
      <Stack spacing={2}>
        <Typography variant="h6" component="h2" sx={{ fontWeight: 600 }}>
          Oturumunuz bulunamadı
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Operon Puantaj'a Kolektif360 portalı üzerinden giriş yapılır. Lütfen portal.kolektif360.com
          adresinden giriş yapıp Puantaj'ı oradan açın.
        </Typography>
        <Button component="a" href={PORTAL_APPS_URL} variant="contained" size="large" fullWidth>
          Portala git
        </Button>
      </Stack>
    </GirisKarti>
  )
}

/** On-prem: yerel kullanıcı adı/şifre formu (davranış değişmedi). */
function YerelGiris() {
  const { girisYap } = useAuth()
  const navigate = useNavigate()
  const [kullaniciAdi, setKullaniciAdi] = useState('')
  const [parola, setParola] = useState('')
  const [hata, setHata] = useState<string | null>(null)
  const [gonderiliyor, setGonderiliyor] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setHata(null)
    setGonderiliyor(true)
    try {
      await girisYap(kullaniciAdi, parola)
      navigate('/')
    } catch {
      setHata('Kullanıcı adı veya şifre hatalı')
    } finally {
      setGonderiliyor(false)
    }
  }

  return (
    <GirisKarti>
      <form onSubmit={onSubmit}>
        <Stack spacing={2}>
          {hata && <Alert severity="error">{hata}</Alert>}
          <TextField
            label="Kullanıcı adı"
            value={kullaniciAdi}
            onChange={(e) => setKullaniciAdi(e.target.value)}
            autoFocus
            fullWidth
          />
          <TextField
            label="Şifre"
            type="password"
            value={parola}
            onChange={(e) => setParola(e.target.value)}
            fullWidth
          />
          <Button type="submit" variant="contained" size="large" disabled={gonderiliyor} fullWidth>
            Giriş Yap
          </Button>
        </Stack>
      </form>
    </GirisKarti>
  )
}

export function LoginPage() {
  // AUTH_MODE build-time bayraktır (Dockerfile: VITE_AUTH_MODE=saas). Sunucuya sormak
  // gerekmez — oturum bozukken backend'in kendisi de hata veriyor olabilir.
  return AUTH_MODE === 'saas' ? <PortalGirisi /> : <YerelGiris />
}
