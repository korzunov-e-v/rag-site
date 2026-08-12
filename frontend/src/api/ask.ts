import type { Answer } from '../types/ask'
import { apiFetch } from './client'

export async function askQuestion(
  query: string,
): Promise<Answer[]> {
  const response = await apiFetch(
    `/api/v1/ask?query=${encodeURIComponent(query)}`,
    {
      method: 'POST',
    },
  )

  if (!response.ok) {
    throw new Error('Не удалось получить ответ')
  }

  return response.json()
}
