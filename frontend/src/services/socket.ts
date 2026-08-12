import { io, type Socket } from 'socket.io-client'
import { getToken } from './auth'

export const socket: Socket = io('http://localhost:8000', {
  autoConnect: false,
})

export function connectSocket(): void {
  const token = getToken()

  if (!token) {
    return
  }

  socket.auth = {
    token,
  }

  if (!socket.connected) {
    socket.connect()
  }
}

export function disconnectSocket(): void {
  if (socket.connected) {
    socket.disconnect()
  }
}
