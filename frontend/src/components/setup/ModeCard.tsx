import type { ReactNode } from 'react'
import { Box, Paper, Typography } from '@mui/material'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'

interface Props {
  secili: boolean
  baslik: string
  aciklama: string
  ikon: ReactNode
  onClick: () => void
}

export function ModeCard({ secili, baslik, aciklama, ikon, onClick }: Props) {
  return (
    <Paper
      onClick={onClick}
      variant="outlined"
      sx={{
        position: 'relative',
        flex: 1,
        p: 3,
        cursor: 'pointer',
        borderWidth: 2,
        borderColor: secili ? 'primary.main' : 'divider',
        bgcolor: secili ? 'rgba(244, 124, 32, 0.10)' : 'background.paper',
        boxShadow: secili ? '0 4px 14px rgba(244,124,32,0.18)' : 'none',
        transition: (t) => t.transitions.create(['border-color', 'background-color', 'box-shadow'], { duration: 200 }),
        '&:hover': { borderColor: 'primary.main' },
      }}
    >
      {secili && (
        <CheckCircleIcon
          sx={{ position: 'absolute', top: 12, right: 12, color: 'primary.main', fontSize: 22 }}
        />
      )}
      <Box
        sx={{
          width: 44,
          height: 44,
          borderRadius: '50%',
          bgcolor: secili ? 'primary.main' : 'action.hover',
          color: secili ? 'white' : 'text.secondary',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 20,
          fontWeight: 700,
          mb: 2,
          transition: (t) => t.transitions.create(['background-color', 'color'], { duration: 200 }),
        }}
      >
        {ikon}
      </Box>
      <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 0.5, color: secili ? 'primary.dark' : 'text.primary' }}>
        {baslik}
      </Typography>
      <Typography variant="body2" color="text.secondary">
        {aciklama}
      </Typography>
    </Paper>
  )
}
