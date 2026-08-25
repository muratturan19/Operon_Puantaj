import { useEffect, useState } from 'react'
import {
  Button,
  Checkbox,
  FormControlLabel,
  Paper,
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
import { calismaTipiGuncelle, calismaTipiOlustur, listeleCalismaTipleri } from '../services/personelService'
import type { CalismaTipi } from '../services/types'

// weekday() ile aynı kodlama (backend Python date.weekday(): 0=Pzt..6=Paz) — DayCell/JS
// Date.getDay()'den (0=Paz) farklı olduğuna dikkat, karıştırılmamalı.
const HAFTA_GUNLERI = [
  { deger: 0, etiket: 'Pzt' },
  { deger: 1, etiket: 'Sal' },
  { deger: 2, etiket: 'Çar' },
  { deger: 3, etiket: 'Per' },
  { deger: 4, etiket: 'Cum' },
  { deger: 5, etiket: 'Cmt' },
  { deger: 6, etiket: 'Paz' },
]

type DuzenlemeFormu = {
  ad: string
  gunluk_saat: number
  haftalik_gun: number
  hafta_ici_fm_orani: number
  hafta_sonu_fm_orani: number
  resmi_tatil_fm_orani: number
  hafta_tatili_gunleri: number[]
}

// Varsayılan öneri: yalnızca Pazar (kullanıcı geri bildirimi, 2026-07-05 — gerçek örnek:
// 5 gün çalışan Beyaz Yaka'da Cumartesi sadece normal çalışılmayan gün, "hafta tatili"
// (×2 primli) DEĞİL, Cumartesi mesaisi hafta içi oranıyla ödenmeli). haftalik_gun'dan
// bağımsız, her zaman [Pazar] önerilir — şirket isterse ek gün(ler) işaretleyebilir.
function onerilenHaftaTatili(_haftalikGun: number): number[] {
  return [6]
}

function HaftaTatiliSecici({
  secili,
  onDegis,
}: {
  secili: number[]
  onDegis: (yeni: number[]) => void
}) {
  return (
    <Stack direction="row" spacing={0.5} flexWrap="wrap">
      {HAFTA_GUNLERI.map((g) => (
        <FormControlLabel
          key={g.deger}
          sx={{ mr: 0.5 }}
          control={
            <Checkbox
              size="small"
              checked={secili.includes(g.deger)}
              onChange={(e) =>
                onDegis(
                  e.target.checked ? [...secili, g.deger] : secili.filter((d) => d !== g.deger),
                )
              }
            />
          }
          label={g.etiket}
        />
      ))}
    </Stack>
  )
}

export function EmployeeTypesPage() {
  const [liste, setListe] = useState<CalismaTipi[]>([])
  const [form, setForm] = useState({
    kod: '',
    ad: '',
    gunluk_saat: 7.5,
    haftalik_gun: 6,
    hafta_tatili_gunleri: onerilenHaftaTatili(6),
  })
  const [duzenlenenId, setDuzenlenenId] = useState<number | null>(null)
  const [duzenlemeForm, setDuzenlemeForm] = useState<DuzenlemeFormu>({
    ad: '',
    gunluk_saat: 0,
    haftalik_gun: 0,
    hafta_ici_fm_orani: 1.5,
    hafta_sonu_fm_orani: 2.0,
    resmi_tatil_fm_orani: 2.0,
    hafta_tatili_gunleri: [6],
  })

  function yenile() {
    listeleCalismaTipleri().then(setListe)
  }

  useEffect(yenile, [])

  function duzenlemeyeBasla(t: CalismaTipi) {
    setDuzenlenenId(t.id)
    setDuzenlemeForm({
      ad: t.ad,
      gunluk_saat: t.gunluk_saat,
      haftalik_gun: t.haftalik_gun,
      hafta_ici_fm_orani: t.hafta_ici_fm_orani,
      hafta_sonu_fm_orani: t.hafta_sonu_fm_orani,
      resmi_tatil_fm_orani: t.resmi_tatil_fm_orani,
      hafta_tatili_gunleri: t.hafta_tatili_gunleri,
    })
  }

  async function duzenlemeyiKaydet(id: number) {
    await calismaTipiGuncelle(id, duzenlemeForm)
    setDuzenlenenId(null)
    yenile()
  }

  function sabitOranaEsitle() {
    setDuzenlemeForm((f) => ({
      ...f,
      hafta_sonu_fm_orani: f.hafta_ici_fm_orani,
      resmi_tatil_fm_orani: f.hafta_ici_fm_orani,
    }))
  }

  return (
    <Stack spacing={3} sx={{ maxWidth: 1080 }}>
      <Typography variant="h5" sx={{ fontWeight: 700 }}>
        Çalışma Tipleri
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 720 }}>
        Çalışanların günlük/haftalık çalışma saatlerini ve fazla mesai (FM) çarpanlarını
        buradan tanımlayın. Her personel bir çalışma tipine atanır.
      </Typography>

      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Kod</TableCell>
              <TableCell>Ad</TableCell>
              <TableCell align="right">Günlük Saat</TableCell>
              <TableCell align="right">Haftalık Gün</TableCell>
              <TableCell>Hafta Tatili Günleri</TableCell>
              <TableCell align="right">FM Hafta İçi</TableCell>
              <TableCell align="right">FM Hafta Tatili</TableCell>
              <TableCell align="right">FM Resmi Tatil</TableCell>
              <TableCell align="right">İşlem</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {liste.map((t) => {
              const duzenleniyor = duzenlenenId === t.id
              return (
                <TableRow key={t.id}>
                  <TableCell>{t.kod}</TableCell>
                  <TableCell>
                    {duzenleniyor ? (
                      <TextField
                        size="small"
                        value={duzenlemeForm.ad}
                        onChange={(e) => setDuzenlemeForm({ ...duzenlemeForm, ad: e.target.value })}
                      />
                    ) : (
                      t.ad
                    )}
                  </TableCell>
                  <TableCell align="right">
                    {duzenleniyor ? (
                      <TextField
                        type="number"
                        size="small"
                        sx={{ width: 90 }}
                        value={duzenlemeForm.gunluk_saat}
                        onChange={(e) =>
                          setDuzenlemeForm({ ...duzenlemeForm, gunluk_saat: parseFloat(e.target.value) })
                        }
                      />
                    ) : (
                      t.gunluk_saat
                    )}
                  </TableCell>
                  <TableCell align="right">
                    {duzenleniyor ? (
                      <TextField
                        type="number"
                        size="small"
                        sx={{ width: 90 }}
                        value={duzenlemeForm.haftalik_gun}
                        onChange={(e) =>
                          setDuzenlemeForm({ ...duzenlemeForm, haftalik_gun: parseInt(e.target.value, 10) })
                        }
                      />
                    ) : (
                      t.haftalik_gun
                    )}
                  </TableCell>
                  <TableCell>
                    {duzenleniyor ? (
                      <HaftaTatiliSecici
                        secili={duzenlemeForm.hafta_tatili_gunleri}
                        onDegis={(yeni) => setDuzenlemeForm({ ...duzenlemeForm, hafta_tatili_gunleri: yeni })}
                      />
                    ) : (
                      HAFTA_GUNLERI.filter((g) => t.hafta_tatili_gunleri.includes(g.deger))
                        .map((g) => g.etiket)
                        .join(', ')
                    )}
                  </TableCell>
                  <TableCell align="right">
                    {duzenleniyor ? (
                      <TextField
                        type="number"
                        size="small"
                        sx={{ width: 90 }}
                        inputProps={{ step: 0.05 }}
                        value={duzenlemeForm.hafta_ici_fm_orani}
                        onChange={(e) =>
                          setDuzenlemeForm({ ...duzenlemeForm, hafta_ici_fm_orani: parseFloat(e.target.value) })
                        }
                      />
                    ) : (
                      `×${t.hafta_ici_fm_orani}`
                    )}
                  </TableCell>
                  <TableCell align="right">
                    {duzenleniyor ? (
                      <TextField
                        type="number"
                        size="small"
                        sx={{ width: 90 }}
                        inputProps={{ step: 0.05 }}
                        value={duzenlemeForm.hafta_sonu_fm_orani}
                        onChange={(e) =>
                          setDuzenlemeForm({ ...duzenlemeForm, hafta_sonu_fm_orani: parseFloat(e.target.value) })
                        }
                      />
                    ) : (
                      `×${t.hafta_sonu_fm_orani}`
                    )}
                  </TableCell>
                  <TableCell align="right">
                    {duzenleniyor ? (
                      <TextField
                        type="number"
                        size="small"
                        sx={{ width: 90 }}
                        inputProps={{ step: 0.05 }}
                        value={duzenlemeForm.resmi_tatil_fm_orani}
                        onChange={(e) =>
                          setDuzenlemeForm({ ...duzenlemeForm, resmi_tatil_fm_orani: parseFloat(e.target.value) })
                        }
                      />
                    ) : (
                      `×${t.resmi_tatil_fm_orani}`
                    )}
                  </TableCell>
                  <TableCell align="right">
                    {duzenleniyor ? (
                      <Stack direction="row" spacing={1} justifyContent="flex-end" flexWrap="wrap">
                        <Button size="small" onClick={sabitOranaEsitle} title="Üç oranı da Hafta İçi değerine eşitler">
                          Sabit Oran
                        </Button>
                        <Button size="small" onClick={() => setDuzenlenenId(null)}>
                          İptal
                        </Button>
                        <Button size="small" variant="contained" onClick={() => duzenlemeyiKaydet(t.id)}>
                          Kaydet
                        </Button>
                      </Stack>
                    ) : (
                      <Button size="small" onClick={() => duzenlemeyeBasla(t)}>
                        Düzenle
                      </Button>
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
          + Yeni Çalışma Tipi
        </Typography>
        <Stack spacing={2}>
          <Stack direction="row" spacing={2} flexWrap="wrap">
            <TextField
              label="Kod"
              size="small"
              value={form.kod}
              onChange={(e) => setForm({ ...form, kod: e.target.value })}
            />
            <TextField
              label="Ad"
              size="small"
              value={form.ad}
              onChange={(e) => setForm({ ...form, ad: e.target.value })}
            />
            <TextField
              label="Günlük Saat"
              type="number"
              size="small"
              value={form.gunluk_saat}
              onChange={(e) => setForm({ ...form, gunluk_saat: parseFloat(e.target.value) })}
            />
            <TextField
              label="Haftalık Gün"
              type="number"
              size="small"
              value={form.haftalik_gun}
              onChange={(e) => {
                const haftalikGun = parseInt(e.target.value, 10)
                setForm({ ...form, haftalik_gun: haftalikGun, hafta_tatili_gunleri: onerilenHaftaTatili(haftalikGun) })
              }}
            />
            <Button
              variant="contained"
              disabled={!form.kod || !form.ad}
              onClick={async () => {
                await calismaTipiOlustur(form)
                setForm({ kod: '', ad: '', gunluk_saat: 7.5, haftalik_gun: 6, hafta_tatili_gunleri: onerilenHaftaTatili(6) })
                yenile()
              }}
            >
              Ekle
            </Button>
          </Stack>
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="caption" color="text.secondary">
              Hafta Tatili Günleri:
            </Typography>
            <HaftaTatiliSecici
              secili={form.hafta_tatili_gunleri}
              onDegis={(yeni) => setForm({ ...form, hafta_tatili_gunleri: yeni })}
            />
          </Stack>
        </Stack>
      </Paper>
    </Stack>
  )
}
