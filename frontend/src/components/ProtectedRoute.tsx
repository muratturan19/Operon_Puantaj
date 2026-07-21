import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { Box, CircularProgress } from '@mui/material'
import { useAuth } from '../context/AuthContext'

export function ProtectedRoute({
  children,
  gerekliIzin,
}: {
  children: ReactNode
  gerekliIzin?: string
}) {
  const { user, yukleniyor, izniVar } = useAuth()

  if (yukleniyor) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    )
  }

  if (!user) return <Navigate to="/login" replace />
  if (gerekliIzin && !izniVar(gerekliIzin)) return <Navigate to="/" replace />

  return <>{children}</>
}
