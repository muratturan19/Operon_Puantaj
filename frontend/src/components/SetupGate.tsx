import { useEffect, useState, type ReactNode } from 'react'
import { Box, CircularProgress } from '@mui/material'
import { getSetupStatus } from '../services/setupService'
import { SetupWizardPage } from '../pages/SetupWizardPage'

/**
 * Uygulama ağacının en dışında — auth'tan bile önce çalışır, çünkü kurulum
 * tamamlanmadan hiç kullanıcı yoktur, giriş ekranı anlamsızdır.
 */
export function SetupGate({ children }: { children: ReactNode }) {
  const [tamamlandi, setTamamlandi] = useState<boolean | null>(null)

  useEffect(() => {
    getSetupStatus()
      .then((s) => setTamamlandi(s.kurulum_tamamlandi))
      .catch(() => setTamamlandi(true)) // sunucuya ulaşılamıyorsa normal akışa düş, login ekranı hatayı gösterir
  }, [])

  if (tamamlandi === null) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    )
  }

  if (!tamamlandi) {
    return <SetupWizardPage />
  }

  return <>{children}</>
}
