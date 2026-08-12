import { onMounted, onUnmounted } from 'vue'
import { socket } from '../services/socket'

export interface DocumentStatusEvent {
  document_id: number
  status: 'processing' | 'processed' | 'failed'
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
