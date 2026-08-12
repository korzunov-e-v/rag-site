<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import DocumentSidebar from './components/DocumentSidebar.vue'
import Login from './components/Login.vue'
import Search from './components/Search.vue'
import {
  clearAuth,
  getToken,
  isAuthenticated,
} from './services/auth'
import {
  connectSocket,
  disconnectSocket,
  socket,
} from './services/socket'
import { getMe } from './api/auth'

const authenticated = ref(isAuthenticated())
const initializing = ref(true)

async function initializeAuth() {
  const token = getToken()

  if (!token) {
    authenticated.value = false
    initializing.value = false
    return
  }

  try {
    await getMe()

    authenticated.value = true
    connectSocket()
  } catch {
    clearAuth()
    authenticated.value = false
  } finally {
    initializing.value = false
  }
}
function handleAuthenticated() {
  authenticated.value = true
}

function logout() {
  disconnectSocket()
  clearAuth()
  authenticated.value = false
}

onMounted(() => {
  socket.on('connect', () => {
    console.log('Socket.IO connected:', socket.id)
  })

  socket.on('connect_error', (error) => {
    console.error('Socket.IO connection error:', error)
  })

  initializeAuth()
})

onUnmounted(() => {
  socket.off('connect')
  socket.off('connect_error')
})
</script>

<template>
  <div v-if="initializing">
    <div
      class="flex min-h-screen items-center
             justify-center bg-slate-50 text-sm
             text-slate-500"
    >
      Проверяем авторизацию...
    </div>
  </div>

  <Login
    v-else-if="!authenticated"
    @authenticated="handleAuthenticated"
  />

  <div
    v-else
    class="flex h-screen overflow-hidden bg-slate-50"
  >
    <DocumentSidebar />

    <main class="flex min-w-0 flex-1 flex-col">
      <header class="border-b border-slate-200 bg-white">
        <div
          class="flex items-center justify-between
                 px-8 py-5"
        >
          <div>
            <h1 class="text-xl font-semibold text-slate-900">
              RAG
            </h1>

            <p class="mt-1 text-sm text-slate-500">
              Поиск ответов по вашим документам
            </p>
          </div>

          <button
            type="button"
            class="rounded-lg border border-slate-200
                   px-3 py-2 text-sm text-slate-600
                   transition hover:bg-slate-50
                   hover:text-slate-900"
            @click="logout"
          >
            Выйти
          </button>
        </div>
      </header>

      <Search />
    </main>
  </div>
</template>
