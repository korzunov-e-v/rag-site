import type { Document } from '../types/document'
import { apiFetch } from './client'

async function errorMessage(
  response: Response,
  fallback: string,
): Promise<string> {
  try {
    const data = await response.json()

    if (typeof data.detail === 'string') {
      return data.detail
    }
  } catch {
    // Ответ не JSON — показываем общую ошибку.
  }

  return fallback
}

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
    throw new Error(
      await errorMessage(response, 'Не удалось загрузить документ'),
    )
  }

  return response.json()
}

export async function uploadDocumentFromUrl(url: string): Promise<Document> {
  const response = await apiFetch('/api/v1/documents/url', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ url }),
  })

  if (!response.ok) {
    throw new Error(
      await errorMessage(response, 'Не удалось загрузить документ по ссылке'),
    )
  }

  return response.json()
}

export async function setDocumentShared(
  id: number,
  isShared: boolean,
): Promise<Document> {
  const response = await apiFetch(`/api/v1/documents/${id}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ is_shared: isShared }),
  })

  if (!response.ok) {
    throw new Error(
      await errorMessage(response, 'Не удалось изменить доступ к документу'),
    )
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
