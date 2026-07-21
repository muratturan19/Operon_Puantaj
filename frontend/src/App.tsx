import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { CircularProgress, Stack } from '@mui/material'
import { AuthProvider } from './context/AuthContext'
import { ProtectedRoute } from './components/ProtectedRoute'
import { SetupGate } from './components/SetupGate'
import { AppLayout } from './components/AppLayout'
import { LoginPage } from './pages/LoginPage'
import { AttendanceGridPage } from './pages/AttendanceGridPage'
import { AUTH_MODE } from './config/env'

// Sık ziyaret edilmeyen yönetim/ayar sayfaları route bazlı code-splitting ile
// ayrı chunk'lara alındı (ROADMAP.md — Teknik Borç: bundle code-splitting).
// Giriş ve ana puantaj grid'i (yukarıda) kritik yol olduğu için eager kalıyor.
const EmployeesPage = lazy(() => import('./pages/EmployeesPage').then((m) => ({ default: m.EmployeesPage })))
const EmployeeTypesPage = lazy(() =>
  import('./pages/EmployeeTypesPage').then((m) => ({ default: m.EmployeeTypesPage })),
)
const UsersRolesPage = lazy(() => import('./pages/UsersRolesPage').then((m) => ({ default: m.UsersRolesPage })))
const SettingsPage = lazy(() => import('./pages/SettingsPage').then((m) => ({ default: m.SettingsPage })))
const CompanySettingsPage = lazy(() =>
  import('./pages/CompanySettingsPage').then((m) => ({ default: m.CompanySettingsPage })),
)
const GuvenlikPage = lazy(() => import('./pages/GuvenlikPage').then((m) => ({ default: m.GuvenlikPage })))

function SayfaYukleniyor() {
  return (
    <Stack alignItems="center" justifyContent="center" sx={{ py: 8 }}>
      <CircularProgress />
    </Stack>
  )
}

function App() {
  // Kurulum Sihirbazı yalnızca on-prem'e özgü (CLAUDE.md §8.8 madde 4) — SaaS modda
  // kullanıcı/tenant zaten Portal'dan geliyor, wizard'a hiç gerek yok.
  const content = (
    <AuthProvider>
      <Suspense fallback={<SayfaYukleniyor />}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <AppLayout>
                  <AttendanceGridPage />
                </AppLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/personel"
            element={
              <ProtectedRoute gerekliIzin="personel_yonetebilir">
                <AppLayout>
                  <EmployeesPage />
                </AppLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/calisma-tipleri"
            element={
              <ProtectedRoute gerekliIzin="calisma_tipi_yonetebilir">
                <AppLayout>
                  <EmployeeTypesPage />
                </AppLayout>
              </ProtectedRoute>
            }
          />
          {/* Kullanıcılar/Roller sayfası SaaS modda gizli — rol/kullanıcı ataması Portal'dan yapılır (CLAUDE.md §8.8 madde 4). */}
          {AUTH_MODE !== 'saas' && (
            <Route
              path="/kullanicilar"
              element={
                <ProtectedRoute gerekliIzin="kullanici_yonetebilir">
                  <AppLayout>
                    <UsersRolesPage />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
          )}
          <Route
            path="/ayarlar"
            element={
              <ProtectedRoute gerekliIzin="excel_ice_aktarabilir">
                <AppLayout>
                  <SettingsPage />
                </AppLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/sirket-ayarlari"
            element={
              <ProtectedRoute gerekliIzin="sirket_ayarlarini_yonetebilir">
                <AppLayout>
                  <CompanySettingsPage />
                </AppLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/guvenlik"
            element={
              <ProtectedRoute gerekliIzin="audit_gorebilir">
                <AppLayout>
                  <GuvenlikPage />
                </AppLayout>
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </AuthProvider>
  )

  return <BrowserRouter>{AUTH_MODE === 'saas' ? content : <SetupGate>{content}</SetupGate>}</BrowserRouter>
}

export default App
