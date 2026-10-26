/**
 * Arayüze gömülen sürüm — `backend/app/core/version.py::SURUM`'un ikizidir.
 *
 * İkisi aynı kaynak ağaçtan derlendiği için normalde eşittir. Kullanıcının
 * tarayıcısında önbellekten eski bir paket açıksa sunucunun bildirdiği sürümle
 * ayrışır; AppLayout bunu görüp "Sayfayı yenileyin" uyarısı gösterir.
 * CHANGELOG'a yeni başlık eklenince ikisi birlikte güncellenir.
 */
export const FRONTEND_SURUM = '4.9.6'
