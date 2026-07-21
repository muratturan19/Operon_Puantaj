import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, Box, Button, Paper, Stack, TextField, Typography } from '@mui/material'
import { useAuth } from '../context/AuthContext'

export function LoginPage() {
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
      </Paper>
    </Box>
  )
}
