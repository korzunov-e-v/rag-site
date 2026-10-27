import type { Answer } from './ask'

export type MessageRole = 'user' | 'assistant'

export interface Message {
  role: MessageRole
  content: string
}

export type ReplyKind = 'answers' | 'clarification' | 'reply'

export interface ChatTurn {
  id: string
  question: string
  // Запрос, который агент реально отправил в поиск (с учётом истории).
  searchQuery: string | null
  kind: ReplyKind | null
  answers: Answer[]
  text: string | null
  failedDocuments: string[]
  status: 'pending' | 'done' | 'error'
  error: string | null
}

export interface Conversation {
  id: number
  title: string
  updated_at: string
}

export interface ConversationMessage {
  id: number
  role: MessageRole
  kind: 'question' | ReplyKind
  content: string
  answers: Answer[] | null
  created_at: string
}

export interface ConversationDetail extends Conversation {
  messages: ConversationMessage[]
}
