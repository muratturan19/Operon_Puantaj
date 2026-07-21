import { apiClient } from './apiClient'
import type { AuditLogEntry } from './types'

export async function listeleAuditLog(limit = 200): Promise<AuditLogEntry[]> {
  const { data } = await apiClient.get<AuditLogEntry[]>('/audit', { params: { limit } })
  return data
}
