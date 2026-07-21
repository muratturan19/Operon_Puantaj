// Dev'de Vite proxy (/api -> backend) kullanılır, prod'da aynı origin'den servis edilir varsayımıyla boş bırakılır.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'

// Build-time bayrak — Docker imajı 'saas' ile build edilir (Portal SSO, tenant DB routing,
// yerel Kurulum Sihirbazı/Kullanıcılar sayfası kapalı). On-prem installer build'inde varsayılan.
export const AUTH_MODE = (import.meta.env.VITE_AUTH_MODE as string | undefined) ?? 'onprem'
export const PORTAL_APPS_URL = 'https://portal.kolektif360.com/apps'
