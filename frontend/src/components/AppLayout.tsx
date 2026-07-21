import type { ReactNode } from 'react'
import { Link as RouterLink, useLocation } from 'react-router-dom'
import { AppBar, Box, Button, Stack, Toolbar, Typography } from '@mui/material'
import { useAuth } from '../context/AuthContext'
import { AUTH_MODE } from '../config/env'

interface NavItem {
  to: string
  etiket: string
  gerekliIzin?: string
  gizliSaas?: boolean
}

const NAV_ITEMS: NavItem[] = [
  { to: '/', etiket: 'Puantaj' },
  { to: '/personel', etiket: 'Personel', gerekliIzin: 'personel_yonetebilir' },
  { to: '/calisma-tipleri', etiket: 'Çalışma Tipleri', gerekliIzin: 'calisma_tipi_yonetebilir' },
  // Kullanıcılar/Roller SaaS modda gizli — atama Portal'dan yapılır (CLAUDE.md §8.8 madde 4).
  { to: '/kullanicilar', etiket: 'Kullanıcılar', gerekliIzin: 'kullanici_yonetebilir', gizliSaas: true },
  { to: '/ayarlar', etiket: 'Excel Aktarım', gerekliIzin: 'excel_ice_aktarabilir' },
  { to: '/sirket-ayarlari', etiket: 'Şirket Ayarları', gerekliIzin: 'sirket_ayarlarini_yonetebilir' },
  { to: '/guvenlik', etiket: 'Güvenlik', gerekliIzin: 'audit_gorebilir' },
]

export function AppLayout({ children }: { children: ReactNode }) {
  const { user, cikisYap, izniVar } = useAuth()
  const location = useLocation()

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <AppBar position="static" sx={{ bgcolor: 'secondary.main' }} elevation={0}>
        <Toolbar sx={{ gap: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>
            Operon <Box component="span" sx={{ color: 'primary.main' }}>Puantaj</Box>
          </Typography>
          <Stack direction="row" spacing={1} sx={{ flexGrow: 1 }}>
            {NAV_ITEMS.filter(
              (item) =>
                (!item.gerekliIzin || izniVar(item.gerekliIzin)) && !(item.gizliSaas && AUTH_MODE === 'saas'),
            ).map((item) => (
              <Button
                key={item.to}
                component={RouterLink}
                to={item.to}
                sx={{
                  color: 'white',
                  opacity: location.pathname === item.to ? 1 : 0.75,
                  borderBottom: location.pathname === item.to ? '2px solid' : '2px solid transparent',
                  borderColor: 'primary.main',
                  borderRadius: 0,
                }}
              >
                {item.etiket}
              </Button>
            ))}
          </Stack>
          <Typography variant="body2" sx={{ opacity: 0.8 }}>
            {user?.ad_soyad}
          </Typography>
          <Button color="inherit" onClick={cikisYap} size="small">
            Çıkış
          </Button>
        </Toolbar>
      </AppBar>
      <Box sx={{ p: { xs: 2, md: 4 } }}>{children}</Box>
    </Box>
  )
}
