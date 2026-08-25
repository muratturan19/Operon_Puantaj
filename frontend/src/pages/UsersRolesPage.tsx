import { useEffect, useState } from 'react'
import {
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import {
  kullaniciGuncelle,
  kullaniciOlustur,
  listeleKullanicilar,
  listeleRoller,
  parolaDegistir,
  type Kullanici,
  type Rol,
} from '../services/usersService'
import { useAuth } from '../context/AuthContext'

type DuzenlemeFormu = { ad_soyad: string; email: string; rol_id: number; aktif: boolean }

export function UsersRolesPage() {
  const { user: benimKullanicim } = useAuth()
  const [kullanicilar, setKullanicilar] = useState<Kullanici[]>([])
  const [roller, setRoller] = useState<Rol[]>([])
  const [form, setForm] = useState({ kullanici_adi: '', ad_soyad: '', parola: '', rol_id: 0 })
  const [duzenlenenId, setDuzenlenenId] = useState<number | null>(null)
  const [duzenlemeForm, setDuzenlemeForm] = useState<DuzenlemeFormu>({
    ad_soyad: '',
    email: '',
    rol_id: 0,
    aktif: true,
  })
  const [sifreDialogId, setSifreDialogId] = useState<number | null>(null)
  const [yeniSifre, setYeniSifre] = useState('')

  function yenile() {
    listeleKullanicilar().then(setKullanicilar)
  }

  useEffect(() => {
    yenile()
    listeleRoller().then((r) => {
      setRoller(r)
      if (r.length > 0) setForm((f) => ({ ...f, rol_id: r[0].id }))
    })
  }, [])

  const rolAdi = (id: number) => roller.find((r) => r.id === id)?.ad ?? '—'

  function duzenlemeyeBasla(k: Kullanici) {
    setDuzenlenenId(k.id)
    setDuzenlemeForm({ ad_soyad: k.ad_soyad, email: k.email ?? '', rol_id: k.rol_id, aktif: k.aktif })
  }

  async function duzenlemeyiKaydet(id: number) {
    await kullaniciGuncelle(id, {
      ad_soyad: duzenlemeForm.ad_soyad,
      email: duzenlemeForm.email || null,
      rol_id: duzenlemeForm.rol_id,
      aktif: duzenlemeForm.aktif,
    })
    setDuzenlenenId(null)
    yenile()
  }

  async function sifreyiKaydet() {
    if (sifreDialogId == null || !yeniSifre) return
    await parolaDegistir(sifreDialogId, yeniSifre)
    setSifreDialogId(null)
    setYeniSifre('')
  }

  return (
    <Stack spacing={3} sx={{ maxWidth: 960 }}>
      <Typography variant="h5" sx={{ fontWeight: 700 }}>
        Kullanıcılar
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 720 }}>
        Programa giriş yapacak kullanıcıları ve rollerini (yetkilerini) buradan yönetin — yeni
        hesap açın, rol değiştirin, pasife alın veya şifre sıfırlayın.
      </Typography>

      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Kullanıcı Adı</TableCell>
              <TableCell>Ad Soyad</TableCell>
              <TableCell>E-posta</TableCell>
              <TableCell>Rol</TableCell>
              <TableCell>Durum</TableCell>
              <TableCell align="right">İşlem</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {kullanicilar.map((k) => {
              const duzenleniyor = duzenlenenId === k.id
              const kendisi = k.id === benimKullanicim?.id
              return (
                <TableRow key={k.id}>
                  <TableCell>{k.kullanici_adi}</TableCell>
                  <TableCell>
                    {duzenleniyor ? (
                      <TextField
                        size="small"
                        value={duzenlemeForm.ad_soyad}
                        onChange={(e) => setDuzenlemeForm({ ...duzenlemeForm, ad_soyad: e.target.value })}
                      />
                    ) : (
                      k.ad_soyad
                    )}
                  </TableCell>
                  <TableCell>
                    {duzenleniyor ? (
                      <TextField
                        size="small"
                        value={duzenlemeForm.email}
                        onChange={(e) => setDuzenlemeForm({ ...duzenlemeForm, email: e.target.value })}
                      />
                    ) : (
                      k.email ?? '—'
                    )}
                  </TableCell>
                  <TableCell>
                    {duzenleniyor ? (
                      <Select
                        size="small"
                        value={duzenlemeForm.rol_id}
                        onChange={(e) => setDuzenlemeForm({ ...duzenlemeForm, rol_id: Number(e.target.value) })}
                      >
                        {roller.map((r) => (
                          <MenuItem key={r.id} value={r.id}>
                            {r.ad}
                          </MenuItem>
                        ))}
                      </Select>
                    ) : (
                      rolAdi(k.rol_id)
                    )}
                  </TableCell>
                  <TableCell>
                    {duzenleniyor ? (
                      <FormControlLabel
                        control={
                          <Checkbox
                            checked={duzenlemeForm.aktif}
                            disabled={kendisi}
                            onChange={(e) => setDuzenlemeForm({ ...duzenlemeForm, aktif: e.target.checked })}
                          />
                        }
                        label="Aktif"
                      />
                    ) : (
                      k.aktif ? 'Aktif' : 'Pasif'
                    )}
                  </TableCell>
                  <TableCell align="right">
                    {duzenleniyor ? (
                      <Stack direction="row" spacing={1} justifyContent="flex-end">
                        <Button size="small" onClick={() => setDuzenlenenId(null)}>
                          İptal
                        </Button>
                        <Button size="small" variant="contained" onClick={() => duzenlemeyiKaydet(k.id)}>
                          Kaydet
                        </Button>
                      </Stack>
                    ) : (
                      <Stack direction="row" spacing={1} justifyContent="flex-end">
                        <Button size="small" onClick={() => setSifreDialogId(k.id)}>
                          Şifre Sıfırla
                        </Button>
                        <Button size="small" onClick={() => duzenlemeyeBasla(k)}>
                          Düzenle
                        </Button>
                      </Stack>
                    )}
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </TableContainer>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle2" sx={{ mb: 2 }}>
          + Yeni Kullanıcı
        </Typography>
        <Stack direction="row" spacing={2} flexWrap="wrap">
          <TextField
            label="Kullanıcı Adı"
            size="small"
            value={form.kullanici_adi}
            onChange={(e) => setForm({ ...form, kullanici_adi: e.target.value })}
          />
          <TextField
            label="Ad Soyad"
            size="small"
            value={form.ad_soyad}
            onChange={(e) => setForm({ ...form, ad_soyad: e.target.value })}
          />
          <TextField
            label="Geçici Şifre"
            type="password"
            size="small"
            value={form.parola}
            onChange={(e) => setForm({ ...form, parola: e.target.value })}
          />
          <Select
            size="small"
            value={form.rol_id || ''}
            onChange={(e) => setForm({ ...form, rol_id: Number(e.target.value) })}
          >
            {roller.map((r) => (
              <MenuItem key={r.id} value={r.id}>
                {r.ad}
              </MenuItem>
            ))}
          </Select>
          <Button
            variant="contained"
            disabled={!form.kullanici_adi || !form.ad_soyad || !form.parola || !form.rol_id}
            onClick={async () => {
              await kullaniciOlustur(form)
              setForm({ kullanici_adi: '', ad_soyad: '', parola: '', rol_id: form.rol_id })
              yenile()
            }}
          >
            Ekle
          </Button>
        </Stack>
      </Paper>

      <Dialog open={sifreDialogId != null} onClose={() => setSifreDialogId(null)}>
        <DialogTitle>Şifre Sıfırla</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            label="Yeni Şifre"
            type="password"
            size="small"
            fullWidth
            sx={{ mt: 1, minWidth: 280 }}
            value={yeniSifre}
            onChange={(e) => setYeniSifre(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSifreDialogId(null)}>İptal</Button>
          <Button variant="contained" disabled={!yeniSifre} onClick={sifreyiKaydet}>
            Kaydet
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  )
}
