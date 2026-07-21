import { useEffect, useState } from 'react'
import {
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
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
import { listeleCalismaTipleri, listelePersonel, personelGuncelle, personelOlustur } from '../services/personelService'
import type { CalismaTipi, Personel } from '../services/types'

function bugun(): string {
  // toISOString() UTC'ye çevirir — TR saatinde gece yarısına yakın saatlerde
  // bir gün geriye kayar (UTC+3). Yerel tarih bileşenleriyle oluşturuluyor.
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

type DuzenlemeFormu = {
  calisma_tipi_id: number
  maas: number
  ng: number
  ise_baslama_tarihi: string | null
}

export function EmployeesPage() {
  const [liste, setListe] = useState<Personel[]>([])
  const [tipler, setTipler] = useState<CalismaTipi[]>([])
  const [form, setForm] = useState({ ad_soyad: '', calisma_tipi_id: 0, maas: 0, ng: 30, ise_baslama_tarihi: bugun() })
  const [cikisDialog, setCikisDialog] = useState<{ personel: Personel; tarih: string } | null>(null)
  const [duzenlenenId, setDuzenlenenId] = useState<number | null>(null)
  const [duzenlemeForm, setDuzenlemeForm] = useState<DuzenlemeFormu>({
    calisma_tipi_id: 0,
    maas: 0,
    ng: 30,
    ise_baslama_tarihi: null,
  })

  function yenile() {
    listelePersonel().then(setListe)
  }

  useEffect(() => {
    yenile()
    listeleCalismaTipleri().then((t) => {
      setTipler(t)
      if (t.length > 0) setForm((f) => ({ ...f, calisma_tipi_id: t[0].id }))
    })
  }, [])

  const tipAdi = (id: number) => tipler.find((t) => t.id === id)?.ad ?? '—'

  async function isteCikar(personel: Personel, tarih: string) {
    await personelGuncelle(personel.id, { isten_cikis_tarihi: tarih })
    setCikisDialog(null)
    yenile()
  }

  async function geriAl(personel: Personel) {
    await personelGuncelle(personel.id, { isten_cikis_tarihi: null })
    yenile()
  }

  function duzenlemeyeBasla(p: Personel) {
    setDuzenlenenId(p.id)
    setDuzenlemeForm({
      calisma_tipi_id: p.calisma_tipi_id,
      maas: p.maas ?? 0,
      ng: p.ng,
      ise_baslama_tarihi: p.ise_baslama_tarihi,
    })
  }

  async function duzenlemeyiKaydet(id: number) {
    await personelGuncelle(id, duzenlemeForm)
    setDuzenlenenId(null)
    yenile()
  }

  return (
    <Stack spacing={3} sx={{ maxWidth: 1080 }}>
      <Typography variant="h5" sx={{ fontWeight: 700 }}>
        Personel
      </Typography>

      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Ad Soyad</TableCell>
              <TableCell>Çalışma Tipi</TableCell>
              <TableCell align="right">Maaş</TableCell>
              <TableCell align="right" title="Yalnızca referans/başlangıç değeri — aylık hesaplama, dönemin takvim gün sayısını kullanır (Puantaj sayfasından kişi bazında istisna girilebilir).">
                N.G
              </TableCell>
              <TableCell>İşe Giriş</TableCell>
              <TableCell>İşten Çıkış</TableCell>
              <TableCell>Durum</TableCell>
              <TableCell align="right">İşlem</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {liste.map((p) => {
              const duzenleniyor = duzenlenenId === p.id
              return (
                <TableRow key={p.id}>
                  <TableCell>{p.ad_soyad}</TableCell>
                  <TableCell>
                    {duzenleniyor ? (
                      <Select
                        size="small"
                        value={duzenlemeForm.calisma_tipi_id}
                        onChange={(e) =>
                          setDuzenlemeForm({ ...duzenlemeForm, calisma_tipi_id: Number(e.target.value) })
                        }
                      >
                        {tipler.map((t) => (
                          <MenuItem key={t.id} value={t.id}>
                            {t.ad}
                          </MenuItem>
                        ))}
                      </Select>
                    ) : (
                      tipAdi(p.calisma_tipi_id)
                    )}
                  </TableCell>
                  <TableCell align="right">
                    {duzenleniyor ? (
                      <TextField
                        type="number"
                        size="small"
                        sx={{ width: 110 }}
                        value={duzenlemeForm.maas}
                        onChange={(e) => setDuzenlemeForm({ ...duzenlemeForm, maas: parseFloat(e.target.value) })}
                      />
                    ) : p.maas != null ? (
                      `${p.maas.toLocaleString('tr-TR')} ₺`
                    ) : (
                      '—'
                    )}
                  </TableCell>
                  <TableCell align="right">
                    {duzenleniyor ? (
                      <TextField
                        type="number"
                        size="small"
                        sx={{ width: 80 }}
                        value={duzenlemeForm.ng}
                        onChange={(e) => setDuzenlemeForm({ ...duzenlemeForm, ng: parseInt(e.target.value, 10) })}
                      />
                    ) : (
                      p.ng
                    )}
                  </TableCell>
                  <TableCell>
                    {duzenleniyor ? (
                      <TextField
                        type="date"
                        size="small"
                        value={duzenlemeForm.ise_baslama_tarihi ?? ''}
                        onChange={(e) =>
                          setDuzenlemeForm({ ...duzenlemeForm, ise_baslama_tarihi: e.target.value || null })
                        }
                        InputLabelProps={{ shrink: true }}
                      />
                    ) : (
                      p.ise_baslama_tarihi ?? '—'
                    )}
                  </TableCell>
                  <TableCell>{p.isten_cikis_tarihi ?? '—'}</TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={p.aktif ? 'Aktif' : 'Ayrıldı'}
                      color={p.aktif ? 'success' : 'default'}
                    />
                  </TableCell>
                  <TableCell align="right">
                    {duzenleniyor ? (
                      <Stack direction="row" spacing={1} justifyContent="flex-end">
                        <Button size="small" onClick={() => setDuzenlenenId(null)}>
                          İptal
                        </Button>
                        <Button size="small" variant="contained" onClick={() => duzenlemeyiKaydet(p.id)}>
                          Kaydet
                        </Button>
                      </Stack>
                    ) : (
                      <Stack direction="row" spacing={1} justifyContent="flex-end">
                        <Button size="small" onClick={() => duzenlemeyeBasla(p)}>
                          Düzenle
                        </Button>
                        {p.aktif ? (
                          <Button
                            size="small"
                            color="error"
                            onClick={() => setCikisDialog({ personel: p, tarih: bugun() })}
                          >
                            İşten Çıkar
                          </Button>
                        ) : (
                          <Button size="small" onClick={() => geriAl(p)}>
                            Geri Al
                          </Button>
                        )}
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
          + Yeni Personel
        </Typography>
        <Stack direction="row" spacing={2} flexWrap="wrap">
          <TextField
            label="Ad Soyad"
            size="small"
            value={form.ad_soyad}
            onChange={(e) => setForm({ ...form, ad_soyad: e.target.value })}
          />
          <Select
            size="small"
            value={form.calisma_tipi_id || ''}
            onChange={(e) => setForm({ ...form, calisma_tipi_id: Number(e.target.value) })}
          >
            {tipler.map((t) => (
              <MenuItem key={t.id} value={t.id}>
                {t.ad}
              </MenuItem>
            ))}
          </Select>
          <TextField
            label="Maaş"
            type="number"
            size="small"
            value={form.maas}
            onChange={(e) => setForm({ ...form, maas: parseFloat(e.target.value) })}
          />
          <TextField
            label="N.G"
            type="number"
            size="small"
            value={form.ng}
            onChange={(e) => setForm({ ...form, ng: parseInt(e.target.value, 10) })}
          />
          <TextField
            label="İşe Giriş Tarihi"
            type="date"
            size="small"
            value={form.ise_baslama_tarihi}
            onChange={(e) => setForm({ ...form, ise_baslama_tarihi: e.target.value })}
            InputLabelProps={{ shrink: true }}
          />
          <Button
            variant="contained"
            disabled={!form.ad_soyad || !form.calisma_tipi_id}
            onClick={async () => {
              await personelOlustur(form)
              setForm({ ...form, ad_soyad: '', maas: 0 })
              yenile()
            }}
          >
            Ekle
          </Button>
        </Stack>
      </Paper>

      <Dialog open={cikisDialog !== null} onClose={() => setCikisDialog(null)}>
        <DialogTitle>{cikisDialog?.personel.ad_soyad} — İşten Çıkış</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Son çalıştığı gün. Bu tarihe kadar (dahil) puantaj girilebilir; sonraki
            aylarda listede görünmez, çıktığı ayın sonuna kadar görünmeye devam eder.
          </Typography>
          <TextField
            label="Son Çalışılan Gün"
            type="date"
            size="small"
            fullWidth
            value={cikisDialog?.tarih ?? ''}
            onChange={(e) => setCikisDialog((d) => (d ? { ...d, tarih: e.target.value } : d))}
            InputLabelProps={{ shrink: true }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCikisDialog(null)}>İptal</Button>
          <Button
            variant="contained"
            color="error"
            onClick={() => cikisDialog && isteCikar(cikisDialog.personel, cikisDialog.tarih)}
          >
            İşten Çıkar
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  )
}
