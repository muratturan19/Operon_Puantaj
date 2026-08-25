import { useEffect, useState } from 'react'
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Chip,
  Paper,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  Typography,
} from '@mui/material'
import { listeleAuditLog } from '../services/auditService'
import { listeleHatalar } from '../services/hataService'
import type { AuditLogEntry, HataKaydi } from '../services/types'

const AKSIYON_RENK: Record<string, 'success' | 'warning' | 'error'> = {
  create: 'success',
  update: 'warning',
  delete: 'error',
}

export function GuvenlikPage() {
  const [sekme, setSekme] = useState(0)
  const [kayitlar, setKayitlar] = useState<AuditLogEntry[]>([])
  const [hatalar, setHatalar] = useState<HataKaydi[]>([])

  useEffect(() => {
    listeleAuditLog().then(setKayitlar)
    listeleHatalar().then(setHatalar).catch(() => setHatalar([]))
  }, [])

  return (
    <>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 1 }}>
        Güvenlik
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2, maxWidth: 720 }}>
        Bu bir hesap/şifre ayarı sayfası DEĞİLDİR. Puantajda ve parametrelerde yapılan her
        değişikliğin kimin tarafından ve ne zaman yapıldığının kaydını, ayrıca sunucuda oluşan
        hataları gösterir. Kendi şifrenizi değiştirmek için sağ üstteki "Şifremi Değiştir"
        butonunu kullanın.
      </Typography>

      <Tabs value={sekme} onChange={(_, v) => setSekme(v)} sx={{ mb: 2 }}>
        <Tab label={`Denetim Kaydı (${kayitlar.length})`} />
        <Tab label={`Sunucu Hataları (${hatalar.length})`} />
      </Tabs>

      {sekme === 0 && (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Zaman</TableCell>
                <TableCell>Kullanıcı</TableCell>
                <TableCell>Varlık</TableCell>
                <TableCell>Aksiyon</TableCell>
                <TableCell>Değişiklikler</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {kayitlar.map((k) => (
                <TableRow key={k.id}>
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>{new Date(k.zaman).toLocaleString('tr-TR')}</TableCell>
                  <TableCell>{k.aktor_adi}</TableCell>
                  <TableCell>
                    {k.entity_tipi} #{k.entity_id}
                  </TableCell>
                  <TableCell>
                    <Chip size="small" label={k.aksiyon} color={AKSIYON_RENK[k.aksiyon] ?? 'default'} />
                  </TableCell>
                  <TableCell sx={{ fontSize: 12, fontFamily: 'monospace' }}>
                    {Object.entries(k.changes)
                      .map(([alan, d]) => `${alan}: ${JSON.stringify(d.old)} → ${JSON.stringify(d.new)}`)
                      .join(', ')}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {sekme === 1 && (
        <>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Kullanıcıya bir hata ekranı çıktığında gösterilen <b>E-xxxxxxxx</b> kodu buradaki
            kayıtla birebir eşleşir — destek ekibine o kodu iletmeniz yeterlidir.
          </Typography>
          {hatalar.length === 0 ? (
            <Paper variant="outlined" sx={{ p: 3 }}>
              <Typography variant="body2" color="text.secondary">
                Kayıtlı sunucu hatası yok.
              </Typography>
            </Paper>
          ) : (
            hatalar.map((h) => (
              <Accordion key={h.id} disableGutters variant="outlined">
                <AccordionSummary>
                  <Typography sx={{ fontFamily: 'monospace', fontWeight: 700, mr: 2 }}>{h.istek_id}</Typography>
                  <Typography sx={{ mr: 2, whiteSpace: 'nowrap' }}>
                    {new Date(h.zaman).toLocaleString('tr-TR')}
                  </Typography>
                  <Typography sx={{ mr: 2 }} color="error">
                    {h.hata_tipi}
                  </Typography>
                  <Typography color="text.secondary" noWrap>
                    {h.metod} {h.yol}
                    {h.sorgu ? `?${h.sorgu}` : ''} — {h.kullanici ?? '-'}
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Typography sx={{ mb: 1 }}>{h.mesaj}</Typography>
                  <Typography
                    component="pre"
                    sx={{ fontSize: 11, fontFamily: 'monospace', overflowX: 'auto', m: 0 }}
                  >
                    {h.traceback_metni}
                  </Typography>
                </AccordionDetails>
              </Accordion>
            ))
          )}
        </>
      )}
    </>
  )
}
