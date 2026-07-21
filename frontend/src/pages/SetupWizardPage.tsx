import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Alert,
  Box,
  Button,
  Fade,
  FormControlLabel,
  Paper,
  Stack,
  Step,
  StepLabel,
  Stepper,
  Switch,
  TextField,
  Typography,
} from '@mui/material'
import { ModeCard } from '../components/setup/ModeCard'
import { completeSetup } from '../services/setupService'

type Mod = 'tek' | 'cok'

interface WizardState {
  sirketAdi: string
  mod: Mod | null
  kullaniciAdi: string
  adSoyad: string
  parola: string
  parolaTekrar: string
  kullaniciMaasGorebilir: boolean
}

const BASLANGIC: WizardState = {
  sirketAdi: '',
  mod: null,
  kullaniciAdi: '',
  adSoyad: '',
  parola: '',
  parolaTekrar: '',
  kullaniciMaasGorebilir: false,
}

export function SetupWizardPage() {
  const navigate = useNavigate()
  const [state, setState] = useState<WizardState>(BASLANGIC)
  const [adim, setAdim] = useState(0)
  const [gonderiliyor, setGonderiliyor] = useState(false)
  const [hata, setHata] = useState<string | null>(null)

  const cokKullanici = state.mod === 'cok'

  const adimlar = useMemo(
    () =>
      [
        'Şirket',
        'Kurulum Modu',
        'Admin Hesabı',
        ...(cokKullanici ? ['Maaş Görünürlüğü'] : []),
        'Özet',
      ],
    [cokKullanici],
  )

  function guncelle<K extends keyof WizardState>(alan: K, deger: WizardState[K]) {
    setState((s) => ({ ...s, [alan]: deger }))
  }

  function ileriUygunMu(): boolean {
    switch (adimlar[adim]) {
      case 'Şirket':
        return state.sirketAdi.trim().length > 1
      case 'Kurulum Modu':
        return state.mod !== null
      case 'Admin Hesabı':
        return (
          state.kullaniciAdi.trim().length > 2 &&
          state.adSoyad.trim().length > 1 &&
          state.parola.length >= 6 &&
          state.parola === state.parolaTekrar
        )
      default:
        return true
    }
  }

  async function tamamla() {
    if (!state.mod) return
    setGonderiliyor(true)
    setHata(null)
    try {
      await completeSetup({
        sirket_adi: state.sirketAdi.trim(),
        mod: state.mod,
        admin: {
          kullanici_adi: state.kullaniciAdi.trim(),
          ad_soyad: state.adSoyad.trim(),
          parola: state.parola,
        },
        kullanici_maas_gorebilir: cokKullanici ? state.kullaniciMaasGorebilir : false,
      })
      navigate('/')
      window.location.reload() // AuthContext'i temiz baştan yüklesin
    } catch {
      setHata('Kurulum tamamlanamadı. Sunucu bağlantısını kontrol edin.')
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
        p: 2,
      }}
    >
      <Paper elevation={0} sx={{ p: { xs: 3, sm: 5 }, width: '100%', maxWidth: 640, border: '1px solid', borderColor: 'divider' }}>
        <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>
          Operon <Box component="span" sx={{ color: 'primary.main' }}>Puantaj</Box>
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
          Kurulum Sihirbazı — birkaç adımda hazır
        </Typography>

        <Stepper activeStep={adim} alternativeLabel sx={{ mb: 5 }}>
          {adimlar.map((etiket) => (
            <Step key={etiket}>
              <StepLabel>{etiket}</StepLabel>
            </Step>
          ))}
        </Stepper>

        {hata && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {hata}
          </Alert>
        )}

        <Fade in key={adim} timeout={200}>
          <Box sx={{ minHeight: 220 }}>
            {adimlar[adim] === 'Şirket' && (
              <Stack spacing={2}>
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                  Şirketinizin adı nedir?
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Bu ad, uygulama içinde ve dışa aktarılan raporlarda görünür.
                </Typography>
                <TextField
                  autoFocus
                  label="Şirket adı"
                  value={state.sirketAdi}
                  onChange={(e) => guncelle('sirketAdi', e.target.value)}
                  fullWidth
                />
              </Stack>
            )}

            {adimlar[adim] === 'Kurulum Modu' && (
              <Stack spacing={2}>
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                  Nasıl kullanılacak?
                </Typography>
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                  <ModeCard
                    secili={state.mod === 'tek'}
                    baslik="Tek Kullanıcı"
                    aciklama="Sadece siz kullanacaksınız. Bu bilgisayarda da çalışabilir."
                    ikon="1"
                    onClick={() => guncelle('mod', 'tek')}
                  />
                  <ModeCard
                    secili={state.mod === 'cok'}
                    baslik="Çok Kullanıcı"
                    aciklama="Birden fazla kişi erişecek — sunucuda kurulmalı, roller ayrı ayrı yönetilir."
                    ikon="+"
                    onClick={() => guncelle('mod', 'cok')}
                  />
                </Stack>
              </Stack>
            )}

            {adimlar[adim] === 'Admin Hesabı' && (
              <Stack spacing={2}>
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                  Yönetici hesabınızı oluşturun
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Bu hesap tam yetkiye sahip olacak — personel, ayarlar ve diğer kullanıcıları yönetebilir.
                </Typography>
                <TextField
                  autoFocus
                  label="Kullanıcı adı"
                  value={state.kullaniciAdi}
                  onChange={(e) => guncelle('kullaniciAdi', e.target.value)}
                  fullWidth
                />
                <TextField
                  label="Ad Soyad"
                  value={state.adSoyad}
                  onChange={(e) => guncelle('adSoyad', e.target.value)}
                  fullWidth
                />
                <Stack direction="row" spacing={2}>
                  <TextField
                    label="Şifre"
                    type="password"
                    value={state.parola}
                    onChange={(e) => guncelle('parola', e.target.value)}
                    helperText="En az 6 karakter"
                    fullWidth
                  />
                  <TextField
                    label="Şifre (tekrar)"
                    type="password"
                    value={state.parolaTekrar}
                    onChange={(e) => guncelle('parolaTekrar', e.target.value)}
                    error={state.parolaTekrar.length > 0 && state.parola !== state.parolaTekrar}
                    helperText={
                      state.parolaTekrar.length > 0 && state.parola !== state.parolaTekrar
                        ? 'Şifreler eşleşmiyor'
                        : ' '
                    }
                    fullWidth
                  />
                </Stack>
              </Stack>
            )}

            {adimlar[adim] === 'Maaş Görünürlüğü' && (
              <Stack spacing={2}>
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                  Kullanıcı rolü maaş tutarlarını görebilsin mi?
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Puantajı günlük giren kişiler (Kullanıcı rolü) için. Varsayılan olarak
                  gizlidir — sadece saat cinsinden eksik/fazla mesai görürler, ₺ tutarı görmezler.
                  Admin ve GM rolleri bu ayardan etkilenmez, her zaman tüm tutarları görür.
                </Typography>
                <Paper variant="outlined" sx={{ p: 2.5 }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={state.kullaniciMaasGorebilir}
                        onChange={(e) => guncelle('kullaniciMaasGorebilir', e.target.checked)}
                      />
                    }
                    label={
                      state.kullaniciMaasGorebilir
                        ? 'Kullanıcı rolü maaş tutarlarını görebilir'
                        : 'Kullanıcı rolünden maaş tutarları gizli (önerilen)'
                    }
                  />
                </Paper>
              </Stack>
            )}

            {adimlar[adim] === 'Özet' && (
              <Stack spacing={1.5}>
                <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>
                  Kuruluma hazırsınız
                </Typography>
                <SummaryRow etiket="Şirket" deger={state.sirketAdi} />
                <SummaryRow etiket="Kurulum modu" deger={state.mod === 'tek' ? 'Tek Kullanıcı' : 'Çok Kullanıcı'} />
                <SummaryRow etiket="Admin kullanıcı adı" deger={state.kullaniciAdi} />
                {cokKullanici && (
                  <SummaryRow
                    etiket="Kullanıcı rolü maaş görür mü"
                    deger={state.kullaniciMaasGorebilir ? 'Evet' : 'Hayır'}
                  />
                )}
              </Stack>
            )}
          </Box>
        </Fade>

        <Stack direction="row" justifyContent="space-between" sx={{ mt: 5 }}>
          <Button disabled={adim === 0 || gonderiliyor} onClick={() => setAdim((a) => a - 1)}>
            Geri
          </Button>
          {adim < adimlar.length - 1 ? (
            <Button variant="contained" disabled={!ileriUygunMu()} onClick={() => setAdim((a) => a + 1)}>
              İleri
            </Button>
          ) : (
            <Button variant="contained" disabled={gonderiliyor} onClick={tamamla}>
              Kurulumu Tamamla
            </Button>
          )}
        </Stack>
      </Paper>
    </Box>
  )
}

function SummaryRow({ etiket, deger }: { etiket: string; deger: string }) {
  return (
    <Stack direction="row" justifyContent="space-between" sx={{ py: 1, borderBottom: '1px solid', borderColor: 'divider' }}>
      <Typography variant="body2" color="text.secondary">
        {etiket}
      </Typography>
      <Typography variant="body2" sx={{ fontWeight: 600 }}>
        {deger}
      </Typography>
    </Stack>
  )
}
