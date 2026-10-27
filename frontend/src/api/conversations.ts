import type { Conversation, ConversationDetail } from '../types/chat'
import { apiFetch } from './client'

export async function getConversations(): Promise<Conversation[]> {
  const response = await apiFetch('/api/v1/conversations')

  if (!response.ok) {
    throw new Error('Не удалось загрузить историю')
  }

  return response.json()
}

export async function getConversation(
  id: number,
): Promise<ConversationDetail> {
  const response = await apiFetch(`/api/v1/conversations/${id}`)

  if (!response.ok) {
    throw new Error('Не удалось загрузить диалог')
  }

  return response.json()
}

export async function deleteConversation(id: number): Promise<void> {
  const response = await apiFetch(`/api/v1/conversations/${id}`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    throw new Error('Не удалось удалить диалог')
  }
}
