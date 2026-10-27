<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  deleteDocument,
  getDocuments,
  setDocumentShared,
  uploadDocument,
  uploadDocumentFromUrl,
} from '../api/documents'
import type { Document } from '../types/document'
import { getUser } from '../services/auth'
import {
  useDocumentStatus,
  useDocumentUpdated,
  type DocumentStatusEvent,
  type DocumentUpdatedEvent,
} from '../composables/useDocumentStatus'

const documents = ref<Document[]>([])
const loading = ref(true)
const uploading = ref(false)
const error = ref<string | null>(null)
const url = ref('')

const user = getUser()
const isAdmin = user?.role === 'admin'

function isOwn(document: Document): boolean {
  return document.owner_id === user?.id
}

async function toggleShared(document: Document) {
  try {
    error.value = null
    const updated = await setDocumentShared(document.id, !document.is_shared)
    document.is_shared = updated.is_shared
  } catch (err) {
    error.value = err instanceof Error
      ? err.message
      : 'Не удалось изменить доступ к документу'
  }
}

const ACCEPTED_FILES = '.pdf,.txt,.md,.docx,.html,.htm,.png,.jpg,.jpeg'

async function loadDocuments() {
  try {
    loading.value = true
    error.value = null
    documents.value = await getDocuments()
  } catch (err) {
    error.value = err instanceof Error
      ? err.message
      : 'Не удалось загрузить документы'
  } finally {
    loading.value = false
  }
}

async function handleUpload(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]

  if (!file) {
    return
  }

  try {
    uploading.value = true
    error.value = null

    const document = await uploadDocument(file)
    documents.value.unshift(document)
  } catch (err) {
    error.value = err instanceof Error
      ? err.message
      : 'Не удалось загрузить документ'
  } finally {
    uploading.value = false
    input.value = ''
  }
}

async function handleUrlUpload() {
  const value = url.value.trim()

  if (!value || uploading.value) {
    return
  }

  try {
    uploading.value = true
    error.value = null

    const document = await uploadDocumentFromUrl(value)
    documents.value.unshift(document)
    url.value = ''
  } catch (err) {
    error.value = err instanceof Error
      ? err.message
      : 'Не удалось загрузить документ по ссылке'
  } finally {
    uploading.value = false
  }
}

async function handleDelete(document: Document) {
  try {
    error.value = null
    await deleteDocument(document.id)

    documents.value = documents.value.filter(
      (item) => item.id !== document.id,
    )
  } catch (err) {
    error.value = err instanceof Error
      ? err.message
      : 'Не удалось удалить документ'
  }
}

function formatSize(size: number): string {
  if (size < 1024) {
    return `${size} Б`
  }

  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} КБ`
  }

  return `${(size / 1024 / 1024).toFixed(1)} МБ`
}

function statusLabel(status: Document['status']): string {
  switch (status) {
    case 'uploaded':
      return 'Загружен'
    case 'processing':
      return 'Обрабатывается'
    case 'processed':
      return 'Готов'
    case 'failed':
      return 'Ошибка'
  }
}
function handleDocumentStatus(event: DocumentStatusEvent) {
  console.log('📡 DOCUMENT STATUS:', event)

  const document = documents.value.find(
    (item) => item.id === event.document_id,
  )

  if (!document) {
    return
  }

  document.status = event.status
}
useDocumentStatus(handleDocumentStatus)

function handleDocumentUpdated(event: DocumentUpdatedEvent) {
  const document = documents.value.find(
    (item) => item.id === event.document_id,
  )

  if (document) {
    document.description = event.description
  }
}
useDocumentUpdated(handleDocumentUpdated)

onMounted(loadDocuments)
</script>

<template>
  <aside class="flex h-full w-80 shrink-0 flex-col border-r bg-white">
    <div class="flex items-center justify-between border-b p-4">
      <div>
        <h2 class="text-base font-semibold text-slate-900">
          Документы
        </h2>

        <p class="text-sm text-slate-500">
          {{ documents.length }} документов
        </p>
      </div>

      <label
        class="cursor-pointer rounded-lg bg-purple-600 px-3 py-2 text-sm
               font-medium text-white transition hover:bg-purple-700"
        :class="{ 'pointer-events-none opacity-50': uploading }"
      >
        {{ uploading ? 'Загрузка...' : 'Добавить' }}

        <input
          type="file"
          class="hidden"
          :accept="ACCEPTED_FILES"
          :disabled="uploading"
          @change="handleUpload"
        />
      </label>
    </div>

    <form
      class="flex gap-2 border-b p-3"
      @submit.prevent="handleUrlUpload"
    >
      <input
        v-model="url"
        type="url"
        placeholder="Ссылка на страницу или файл"
        class="min-w-0 flex-1 rounded-lg border border-slate-200 px-3 py-2
               text-sm outline-none transition placeholder:text-slate-400
               focus:border-purple-400 focus:ring-2 focus:ring-purple-100"
        :disabled="uploading"
      />

      <button
        type="submit"
        class="shrink-0 rounded-lg border border-slate-200 px-3 py-2 text-sm
               text-slate-600 transition hover:bg-slate-50
               disabled:cursor-not-allowed disabled:opacity-50"
        :disabled="uploading || !url.trim()"
      >
        Импорт
      </button>
    </form>

    <div
      v-if="error"
      class="m-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"
    >
      {{ error }}
    </div>

    <div
      v-if="loading"
      class="p-4 text-sm text-slate-500"
    >
      Загрузка документов...
    </div>

    <div
      v-else-if="documents.length === 0"
      class="p-6 text-center text-sm text-slate-500"
    >
      Документов пока нет
    </div>

    <div
      v-else
      class="flex-1 overflow-y-auto p-2"
    >
      <div
        v-for="document in documents"
        :key="document.id"
        class="group rounded-lg p-3 transition hover:bg-slate-50"
      >
        <div class="flex items-start justify-between gap-2">
          <div class="min-w-0">
            <div class="flex items-center gap-1.5">
              <p
                class="truncate text-sm font-medium text-slate-900"
                :title="document.filename"
              >
                {{ document.filename }}
              </p>

              <span
                v-if="document.is_shared"
                class="shrink-0 rounded bg-purple-50 px-1.5 py-0.5
                       text-[10px] font-medium text-purple-700"
                :title="isOwn(document)
                  ? 'Документ доступен всем пользователям'
                  : 'Общий документ, только для чтения'"
              >
                Общий
              </span>
            </div>

            <p class="mt-1 text-xs text-slate-500">
              {{ formatSize(document.size) }}
              ·
              {{ statusLabel(document.status) }}
            </p>

            <p
              v-if="document.description"
              class="mt-1 line-clamp-2 text-xs leading-5 text-slate-500"
              :title="document.description"
            >
              {{ document.description }}
            </p>
          </div>

          <div
            v-if="isOwn(document)"
            class="flex shrink-0 flex-col items-end gap-1 opacity-0
                   transition group-hover:opacity-100"
          >
            <button
              v-if="isAdmin"
              type="button"
              class="text-xs text-slate-400 hover:text-purple-600"
              @click="toggleShared(document)"
            >
              {{ document.is_shared ? 'Сделать личным' : 'Сделать общим' }}
            </button>

            <button
              type="button"
              class="text-xs text-slate-400 hover:text-red-500"
              title="Удалить"
              @click="handleDelete(document)"
            >
              Удалить
            </button>
          </div>
        </div>
      </div>
    </div>
  </aside>
</template>
