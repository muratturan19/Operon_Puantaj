import axios from 'axios'
import { API_BASE_URL, AUTH_MODE, PORTAL_APPS_URL } from '../config/env'

// withCredentials: SaaS modda Portal SSO'nun set ettiği httponly `access_token`
// cookie'sinin her istekle gönderilmesi için gerekli. Onprem modda zararsız
// (kullanılmayan bir cookie).
export const apiClient = axios.create({ baseURL: API_BASE_URL, withCredentials: true })

const TOKEN_KEY = 'operon_puantaj_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

apiClient.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearToken()
      // SaaS modda yerel /login sayfası anlamsız — oturum Portal SSO'dan gelir,
      // süresi dolunca kullanıcı Portal'daki uygulama listesine geri gönderilir.
      window.location.href = AUTH_MODE === 'saas' ? PORTAL_APPS_URL : '/login'
    }
    return Promise.reject(error)
  },
)
