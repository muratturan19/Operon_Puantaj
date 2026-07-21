import { useState } from 'react'
import {
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  TextField,
} from '@mui/material'
import type { Tatil } from '../../services/types'

interface Props {
  acik: boolean
  onKapat: () => void
  tatiller: Tatil[]
  onEkle: (tarih: string) => void
  onSil: (tatilId: number) => void
}

export function HolidaysDialog({ acik, onKapat, tatiller, onEkle, onSil }: Props) {
  const [yeniTarih, setYeniTarih] = useState('')

  return (
    <Dialog open={acik} onClose={onKapat} maxWidth="xs" fullWidth>
      <DialogTitle>Resmi Tatiller</DialogTitle>
      <DialogContent>
        <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
          <TextField
            type="date"
            size="small"
            value={yeniTarih}
            onChange={(e) => setYeniTarih(e.target.value)}
            fullWidth
          />
          <Button
            variant="contained"
            disabled={!yeniTarih}
            onClick={() => {
              onEkle(yeniTarih)
              setYeniTarih('')
            }}
          >
            Ekle
          </Button>
        </Stack>
        <Stack direction="row" flexWrap="wrap" gap={1}>
          {[...tatiller]
            .sort((a, b) => a.tarih.localeCompare(b.tarih))
            .map((t) => (
              <Chip key={t.id} label={t.tarih} onDelete={() => onSil(t.id)} size="small" />
            ))}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onKapat}>Kapat</Button>
      </DialogActions>
    </Dialog>
  )
}
