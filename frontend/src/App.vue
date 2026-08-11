<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import DocumentSidebar from './components/DocumentSidebar.vue'
import Search from './components/Search.vue'
import { socket } from './services/socket'

onMounted(() => {
  socket.on('connect', () => {
    console.log('Socket.IO connected:', socket.id)
  })

  socket.on('connect_error', (error) => {
    console.error('Socket.IO connection error:', error)
  })
})

onUnmounted(() => {
  socket.off('connect')
  socket.off('connect_error')
})
</script>
<template>
  <div class="flex h-screen overflow-hidden bg-slate-50">
    <DocumentSidebar />

    <main class="flex min-w-0 flex-1 flex-col">
      <header class="border-b border-slate-200 bg-white">
        <div class="px-8 py-5">
          <h1 class="text-xl font-semibold text-slate-900">
            RAG
          </h1>
          <p class="mt-1 text-sm text-slate-500">
            Поиск ответов по вашим документам
          </p>
        </div>
      </header>

      <Search />
    </main>
  </div>
</template>
