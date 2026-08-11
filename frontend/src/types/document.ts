export type DocumentStatus =
  | 'uploaded'
  | 'processing'
  | 'processed'
  | 'failed'

export interface Document {
  id: number
  filename: string
  content_type: string
  size: number
  status: DocumentStatus
  created_at: string
  description: string | null
}
