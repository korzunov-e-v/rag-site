import type { Document } from '../types/document'
import { apiFetch } from './client'

export async function getDocuments(): Promise<Document[]> {
  const response = await apiFetch('/api/v1/documents')

  if (!response.ok) {
    throw new Error('Не удалось получить документы')
  }

  return response.json()
}

export async function uploadDocument(file: File): Promise<Document> {
  const formData = new FormData()
  formData.append('document', file)

  const response = await apiFetch('/api/v1/documents', {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    throw new Error('Не удалось загрузить документ')
  }

  return response.json()
}

export async function deleteDocument(id: number): Promise<void> {
  const response = await apiFetch(`/api/v1/documents/${id}`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    throw new Error('Не удалось удалить документ')
  }
}
