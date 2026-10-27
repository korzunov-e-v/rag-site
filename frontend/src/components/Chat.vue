<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import ChatMessage from './ChatMessage.vue'
import QuestionInput from './QuestionInput.vue'
import SearchResults from './SearchResults.vue'
import type { Answer } from '../types/ask'
import type {
  ChatTurn,
  Conversation,
  ConversationMessage,
} from '../types/chat'
import {
  deleteConversation,
  getConversation,
  getConversations,
} from '../api/conversations'
import { socket } from '../services/socket'

const turns = ref<ChatTurn[]>([])
const conversationId = ref<number | null>(null)
const conversations = ref<Conversation[]>([])
const historyOpen = ref(false)
const loading = ref(false)
const error = ref<string | null>(null)
const thread = ref<HTMLElement | null>(null)

function newTurn(question: string): ChatTurn {
  return {
    id: crypto.randomUUID(),
    question,
    searchQuery: null,
    kind: null,
    answers: [],
    text: null,
    failedDocuments: [],
    status: 'pending',
    error: null,
  }
}

function currentTurn(): ChatTurn | undefined {
  const turn = turns.value[turns.value.length - 1]
  return turn?.status === 'pending' ? turn : undefined
}

function toTurns(messages: ConversationMessage[]): ChatTurn[] {
  const result: ChatTurn[] = []

  for (const message of messages) {
    if (message.role === 'user') {
      result.push({ ...newTurn(message.content), status: 'done' })
      continue
    }

    const turn = result[result.length - 1]

    if (!turn || message.kind === 'question') {
      continue
    }

    turn.kind = message.kind

    if (message.kind === 'answers') {
      turn.searchQuery = message.content
      turn.answers = message.answers ?? []
    } else {
      turn.text = message.content
    }
  }

  return result
}

async function loadConversations() {
  try {
    conversations.value = await getConversations()
  } catch {
    // История — второстепенная функция, чат работает и без неё.
  }
}

async function openConversation(id: number) {
  historyOpen.value = false

  if (loading.value) {
    return
  }

  try {
    error.value = null
    const conversation = await getConversation(id)
    conversationId.value = conversation.id
    turns.value = toTurns(conversation.messages)
  } catch (err) {
    error.value = err instanceof Error
      ? err.message
      : 'Не удалось загрузить диалог'
  }
}

async function removeConversation(id: number) {
  try {
    await deleteConversation(id)
    conversations.value = conversations.value.filter(
      (conversation) => conversation.id !== id,
    )

    if (conversationId.value === id) {
      startNewConversation()
    }
  } catch (err) {
    error.value = err instanceof Error
      ? err.message
      : 'Не удалось удалить диалог'
  }
}

function startNewConversation() {
  if (loading.value) {
    return
  }

  historyOpen.value = false
  conversationId.value = null
  turns.value = []
  error.value = null
}

function ask(query: string) {
  if (loading.value) {
    return
  }

  error.value = null
  loading.value = true
  turns.value.push(newTurn(query))

  socket.emit('ask', {
    query,
    conversation_id: conversationId.value,
  })
}

function handleStarted(data: { conversation_id: number }) {
  conversationId.value = data.conversation_id
}

function handleSearching(data: { query: string }) {
  const turn = currentTurn()

  if (turn) {
    turn.searchQuery = data.query
  }
}

function handleAnswer(answer: Answer) {
  const turn = currentTurn()

  if (!turn) {
    return
  }

  turn.kind = 'answers'
  turn.answers.push(answer)
  turn.answers.sort((a, b) => a.distance - b.distance)
}

function handleText(kind: 'clarification' | 'reply') {
  return (data: { text: string }) => {
    const turn = currentTurn()

    if (turn) {
      turn.kind = kind
      turn.text = data.text
    }
  }
}
const handleClarification = handleText('clarification')
const handleReply = handleText('reply')

function handleDocumentError(data: { filename: string }) {
  currentTurn()?.failedDocuments.push(data.filename)
}

function handleFinished() {
  const turn = currentTurn()

  if (turn) {
    turn.status = 'done'
  }

  loading.value = false
  loadConversations()
}

function handleError(data: { message?: string }) {
  const turn = currentTurn()

  if (turn) {
    turn.status = 'error'
    turn.error = data.message ?? 'Не удалось выполнить поиск'
  }

  loading.value = false
}

const handlers = {
  'ask:started': handleStarted,
  'ask:searching': handleSearching,
  answer: handleAnswer,
  clarification: handleClarification,
  reply: handleReply,
  'document:error': handleDocumentError,
  'ask:finished': handleFinished,
  'ask:error': handleError,
} as const

onMounted(() => {
  for (const [event, handler] of Object.entries(handlers)) {
    socket.on(event, handler)
  }

  loadConversations()
})

onUnmounted(() => {
  for (const [event, handler] of Object.entries(handlers)) {
    socket.off(event, handler)
  }
})

watch(
  turns,
  async () => {
    await nextTick()
    thread.value?.scrollTo({
      top: thread.value.scrollHeight,
      behavior: 'smooth',
    })
  },
  { deep: true },
)
</script>

<template>
  <section class="flex min-h-0 flex-1 flex-col">
    <!-- Toolbar -->

    <div
      class="flex items-center justify-between gap-3 border-b
             border-slate-200 bg-white px-8 py-3"
    >
      <div class="relative">
        <button
          type="button"
          class="rounded-lg border border-slate-200 px-3 py-1.5 text-sm
                 text-slate-600 transition hover:bg-slate-50"
          @click="historyOpen = !historyOpen"
        >
          История
          <span class="text-slate-400">({{ conversations.length }})</span>
        </button>

        <div
          v-if="historyOpen"
          class="absolute left-0 top-full z-10 mt-2 max-h-96 w-80
                 overflow-y-auto rounded-xl border border-slate-200
                 bg-white p-1 shadow-lg"
        >
          <p
            v-if="conversations.length === 0"
            class="p-3 text-sm text-slate-500"
          >
            Диалогов пока нет
          </p>

          <div
            v-for="conversation in conversations"
            :key="conversation.id"
            class="group flex items-center gap-2 rounded-lg px-3 py-2
                   hover:bg-slate-50"
            :class="{ 'bg-purple-50': conversation.id === conversationId }"
          >
            <button
              type="button"
              class="min-w-0 flex-1 truncate text-left text-sm text-slate-700"
              :title="conversation.title"
              @click="openConversation(conversation.id)"
            >
              {{ conversation.title }}
            </button>

            <button
              type="button"
              class="shrink-0 text-xs text-slate-400 opacity-0 transition
                     hover:text-red-500 group-hover:opacity-100"
              @click="removeConversation(conversation.id)"
            >
              Удалить
            </button>
          </div>
        </div>
      </div>

      <button
        type="button"
        class="rounded-lg bg-purple-600 px-3 py-1.5 text-sm font-medium
               text-white transition hover:bg-purple-700
               disabled:cursor-not-allowed disabled:opacity-50"
        :disabled="loading"
        @click="startNewConversation"
      >
        Новый диалог
      </button>
    </div>

    <!-- Thread -->

    <div
      ref="thread"
      class="min-h-0 flex-1 overflow-y-auto"
    >
      <div class="mx-auto w-full max-w-4xl space-y-6 px-6 py-8">
        <div
          v-if="error"
          class="rounded-2xl border border-red-200 bg-red-50 p-4
                 text-sm text-red-700"
        >
          {{ error }}
        </div>

        <!-- Initial state -->

        <div
          v-if="turns.length === 0"
          class="flex min-h-[50vh] items-center justify-center"
        >
          <div class="text-center">
            <div
              class="mx-auto flex h-14 w-14 items-center justify-center
                     rounded-2xl bg-purple-100 text-2xl"
            >
              💬
            </div>

            <h2 class="mt-5 text-2xl font-semibold text-slate-900">
              Спросите о ваших документах
            </h2>

            <p class="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">
              Ответ строится по каждому подходящему документу отдельно.
              Можно задавать уточняющие вопросы — история диалога учитывается.
            </p>
          </div>
        </div>

        <!-- Turns -->

        <div
          v-for="turn in turns"
          :key="turn.id"
          class="space-y-4"
        >
          <ChatMessage :message="{ role: 'user', content: turn.question }" />

          <p
            v-if="turn.searchQuery && turn.searchQuery !== turn.question"
            class="text-xs text-slate-400"
          >
            Искали: «{{ turn.searchQuery }}»
          </p>

          <SearchResults
            v-if="turn.answers.length > 0"
            :answers="turn.answers"
          />

          <ChatMessage
            v-if="turn.text"
            :message="{ role: 'assistant', content: turn.text }"
          />

          <p
            v-if="turn.failedDocuments.length > 0"
            class="text-xs text-amber-600"
          >
            Не удалось получить ответ по документам:
            {{ turn.failedDocuments.join(', ') }}
          </p>

          <div
            v-if="turn.status === 'pending'"
            class="flex items-center gap-2 text-sm text-slate-500"
          >
            <span class="h-2 w-2 animate-pulse rounded-full bg-purple-500" />
            <span>
              {{ turn.searchQuery ? 'Ищем по документам…' : 'Думаем…' }}
            </span>
          </div>

          <div
            v-if="turn.status === 'error'"
            class="rounded-2xl border border-red-200 bg-red-50 p-4
                   text-sm text-red-700"
          >
            {{ turn.error }}
          </div>
        </div>
      </div>
    </div>

    <!-- Input -->

    <div class="border-t border-slate-200 bg-slate-50 px-6 py-4">
      <div class="mx-auto w-full max-w-4xl">
        <QuestionInput
          :disabled="loading"
          @submit="ask"
        />
      </div>
    </div>
  </section>
</template>
