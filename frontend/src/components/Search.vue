<script setup lang="ts">
import {onMounted, onUnmounted, ref} from 'vue'
import SearchResults from './SearchResults.vue'
import type {Answer} from '../types/ask'
import {socket} from '../services/socket'

const query = ref('')
const answers = ref<Answer[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const searched = ref(false)
const receivedCount = ref(0)

function handleAnswer(answer: Answer) {
  answers.value.push(answer)
  receivedCount.value++
}

function handleFinished() {
  loading.value = false
}

function handleError(data: { message?: string }) {
  loading.value = false
  error.value = data.message ?? 'Не удалось выполнить поиск'
}

onMounted(() => {
  socket.on('answer', handleAnswer)
  socket.on('ask:finished', handleFinished)
  socket.on('ask:error', handleError)
})

onUnmounted(() => {
  socket.off('answer', handleAnswer)
  socket.off('ask:finished', handleFinished)
  socket.off('ask:error', handleError)
})

function search() {
  const value = query.value.trim()

  if (!value || loading.value) {
    return
  }

  answers.value = []
  receivedCount.value = 0
  error.value = null
  searched.value = true
  loading.value = true

  socket.emit('ask', {
    query: value,
  })
}
</script>

<template>
  <section class="min-h-0 flex-1 overflow-y-auto">
    <div class="mx-auto w-full max-w-4xl px-6 py-8">

      <!-- Search -->
      <form
          class="mb-8"
          @submit.prevent="search"
      >
        <div
            class="flex items-center gap-2 rounded-2xl border
                 border-slate-200 bg-white p-2 shadow-sm
                 transition focus-within:border-purple-400
                 focus-within:ring-4 focus-within:ring-purple-100"
        >
          <input
              v-model="query"
              type="text"
              placeholder="Что хотите узнать?"
              class="min-w-0 flex-1 bg-transparent px-4 py-3 text-sm
                   text-slate-900 outline-none
                   placeholder:text-slate-400"
              :disabled="loading"
          />

          <button
              type="submit"
              class="flex h-10 items-center justify-center rounded-xl
                   bg-purple-600 px-5 text-sm font-medium text-white
                   transition hover:bg-purple-700
                   disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="loading || !query.trim()"
          >
            {{ loading ? '...' : 'Поиск' }}
          </button>
        </div>
      </form>

      <!-- Empty state -->
      <div
          v-if="!searched"
          class="flex min-h-[55vh] items-center justify-center"
      >
        <div class="text-center">
          <div
              class="mx-auto flex h-14 w-14 items-center justify-center
                   rounded-2xl bg-purple-100 text-2xl"
          >
            🔎
          </div>

          <h2 class="mt-5 text-2xl font-semibold text-slate-900">
            Поиск по документам
          </h2>

          <p class="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">
            Задайте вопрос, и RAG найдёт релевантные документы
            и сформирует отдельный ответ по каждому из них.
          </p>
        </div>
      </div>

      <!-- Loading -->
      <div
          v-if="loading && answers.length === 0"
          class="space-y-4"
      >
        <div
            v-for="i in 2"
            :key="i"
            class="animate-pulse rounded-2xl border border-slate-200
                 bg-white p-6"
        >
          <div class="h-4 w-64 rounded bg-slate-200"/>
          <div class="mt-5 h-4 w-full rounded bg-slate-200"/>
          <div class="mt-3 h-4 w-5/6 rounded bg-slate-200"/>
          <div class="mt-3 h-4 w-2/3 rounded bg-slate-200"/>
        </div>
      </div>

      <!-- Error -->
      <div
          v-else-if="error"
          class="rounded-2xl border border-red-200 bg-red-50 p-5"
      >
        <p class="text-sm font-medium text-red-800">
          Не удалось выполнить поиск
        </p>

        <p class="mt-1 text-sm text-red-600">
          {{ error }}
        </p>
      </div>

      <!-- Results -->
      <template v-if="answers.length > 0">
        <div class="mb-5">
          <p class="text-sm text-slate-500">
            Найдено документов:
            <span class="font-medium text-slate-700">
              {{ answers.length }}
            </span>
          </p>
        </div>

        <SearchResults :answers="answers"/>
        <div
            v-if="loading"
            class="mt-4 flex items-center gap-2 text-sm text-slate-500"
        >
          <span
              class="h-2 w-2 animate-pulse rounded-full bg-purple-500"
          />

                  Ищем по остальным документам…
                  <span>
            Получено ответов: {{ receivedCount }}
          </span>
        </div>
      </template>

      <!-- Nothing found -->
      <div
          v-else
          class="py-20 text-center"
      >
        <div class="text-3xl">¯\_(ツ)_/¯</div>

        <h2 class="mt-4 font-medium text-slate-900">
          Ничего не найдено
        </h2>

        <p class="mt-1 text-sm text-slate-500">
          В загруженных документах нет подходящей информации.
        </p>
      </div>
    </div>
  </section>
</template>
