import { apiClient } from './apiClient'
import type { HataKaydi } from './types'

export async function listeleHatalar(limit = 100): Promise<HataKaydi[]> {
  const { data } = await apiClient.get<HataKaydi[]>('/hatalar', { params: { limit } })
  return data
}
