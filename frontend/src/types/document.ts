export type DocumentStatus =
  | 'uploaded'
  | 'processing'
  | 'processed'
  | 'failed'

export interface Document {
  id: number
  owner_id: number
  filename: string
  content_type: string | null
  size: number
  status: DocumentStatus
  created_at: string
  description: string | null
  is_shared: boolean
}
