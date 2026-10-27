import { onMounted, onUnmounted } from 'vue'
import { socket } from '../services/socket'

export interface DocumentStatusEvent {
  document_id: number
  status: 'processing' | 'processed' | 'failed'
}

export interface DocumentUpdatedEvent {
  document_id: number
  description: string
}

export function useDocumentUpdated(
  onUpdated: (event: DocumentUpdatedEvent) => void,
) {
  onMounted(() => {
    socket.on('document:updated', onUpdated)
  })

  onUnmounted(() => {
    socket.off('document:updated', onUpdated)
  })
}

export function useDocumentStatus(
  onStatus: (event: DocumentStatusEvent) => void,
) {
  onMounted(() => {
  console.log('📡 subscribing to document:status')

  socket.on('document:status', onStatus)
})

  onUnmounted(() => {
    socket.off('document:status', onStatus)
  })
}
