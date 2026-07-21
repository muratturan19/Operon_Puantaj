import { apiClient } from './apiClient'

export interface MappingTemplate {
  id: number
  ad: string
  versiyon: number
  durum: string
}

export async function listeleMappingSablonlari(): Promise<MappingTemplate[]> {
  const { data } = await apiClient.get<MappingTemplate[]>('/excel/mapping-templates')
  return data
}

export interface ImportSonucu {
  donemler_bulundu: string[]
  personel_olusturulan: number
  personel_guncellenen: number
}

export async function excelIceAktar(mappingTemplateId: number, dosya: File): Promise<ImportSonucu> {
  const form = new FormData()
  form.append('dosya', dosya)
  const { data } = await apiClient.post<ImportSonucu>(
    `/excel/import?mapping_template_id=${mappingTemplateId}`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  return data
}

export async function excelDisaAktar(mappingTemplateId: number, donemId?: number): Promise<void> {
  const params: Record<string, number> = { mapping_template_id: mappingTemplateId }
  if (donemId) params.donem_id = donemId

  const response = await apiClient.get('/excel/export', { params, responseType: 'blob' })
  const url = URL.createObjectURL(response.data as Blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'puantaj_export.xlsx'
  a.click()
  URL.revokeObjectURL(url)
}
