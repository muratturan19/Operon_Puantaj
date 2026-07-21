import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { login as loginRequest, me as meRequest, ssoLogout } from '../services/authService'
import { clearToken, getToken } from '../services/apiClient'
import { AUTH_MODE, PORTAL_APPS_URL } from '../config/env'
import type { MeResponse } from '../services/types'

interface AuthContextValue {
  user: MeResponse | null
  yukleniyor: boolean
  girisYap: (kullaniciAdi: string, parola: string) => Promise<void>
  cikisYap: () => void
  izniVar: (izinAnahtari: string) => boolean
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<MeResponse | null>(null)
  const [yukleniyor, setYukleniyor] = useState(true)

  const kullaniciyiYenile = useCallback(async () => {
    // SaaS modda kimlik httponly `access_token` cookie'sinden gelir (localStorage'ta
    // token YOK) — bu yüzden onprem'deki gibi getToken() kısa devresi yapılamaz,
    // /me her zaman denenir; cookie geçersizse zaten 401 ile catch'e düşer.
    if (AUTH_MODE !== 'saas' && !getToken()) {
      setUser(null)
      setYukleniyor(false)
      return
    }
    try {
      const veri = await meRequest()
      setUser(veri)
    } catch {
      clearToken()
      setUser(null)
    } finally {
      setYukleniyor(false)
    }
  }, [])

  useEffect(() => {
    kullaniciyiYenile()
  }, [kullaniciyiYenile])

  const girisYap = useCallback(
    async (kullaniciAdi: string, parola: string) => {
      await loginRequest(kullaniciAdi, parola)
      await kullaniciyiYenile()
    },
    [kullaniciyiYenile],
  )

  const cikisYap = useCallback(() => {
    clearToken()
    setUser(null)
    if (AUTH_MODE === 'saas') {
      // localStorage'ta silinecek bir token yok — asıl oturum httponly cookie'de,
      // JS'ten silinemez; backend'e /sso/logout ile temizlettirip Portal'a dön.
      ssoLogout().finally(() => {
        window.location.href = PORTAL_APPS_URL
      })
    }
  }, [])

  const izniVar = useCallback(
    (izinAnahtari: string) => Boolean(user?.izinler?.[izinAnahtari]),
    [user],
  )

  return (
    <AuthContext.Provider value={{ user, yukleniyor, girisYap, cikisYap, izniVar }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth, AuthProvider içinde kullanılmalı')
  return ctx
}
