import { useEffect, useState } from 'react'
import { Chip, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from '@mui/material'
import { listeleAuditLog } from '../services/auditService'
import type { AuditLogEntry } from '../services/types'

const AKSIYON_RENK: Record<string, 'success' | 'warning' | 'error'> = {
  create: 'success',
  update: 'warning',
  delete: 'error',
}

export function GuvenlikPage() {
  const [kayitlar, setKayitlar] = useState<AuditLogEntry[]>([])

  useEffect(() => {
    listeleAuditLog().then(setKayitlar)
  }, [])

  return (
    <>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 3 }}>
        Güvenlik — Denetim Kaydı
      </Typography>
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
    </>
  )
}
