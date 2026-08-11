export interface AnswerSource {
  chunk_id: number
  text: string
  quote: string
  distance: number
}

export interface Answer {
  document_id: number
  filename: string
  distance: number
  answer: string
  sources: AnswerSource[]
}
