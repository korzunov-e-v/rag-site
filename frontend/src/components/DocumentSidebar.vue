<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  deleteDocument,
  getDocuments,
  uploadDocument,
} from '../api/documents'
import type { Document } from '../types/document'
import {
  useDocumentStatus,
  type DocumentStatusEvent,
} from '../composables/useDocumentStatus'

const documents = ref<Document[]>([])
const loading = ref(true)
const uploading = ref(false)
const error = ref<string | null>(null)

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
  const document = documents.value.find(
    (item) => item.id === event.document_id,
  )

  if (!document) {
    return
  }

  document.status = event.status
}
useDocumentStatus(handleDocumentStatus)

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
          :disabled="uploading"
          @change="handleUpload"
        />
      </label>
    </div>

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
            <p
              class="truncate text-sm font-medium text-slate-900"
              :title="document.filename"
            >
              {{ document.filename }}
            </p>

            <p class="mt-1 text-xs text-slate-500">
              {{ formatSize(document.size) }}
              ·
              {{ statusLabel(document.status) }}
            </p>
          </div>

          <button
            type="button"
            class="shrink-0 text-xs text-slate-400 opacity-0 transition
                   hover:text-red-500 group-hover:opacity-100"
            title="Удалить"
            @click="handleDelete(document)"
          >
            Удалить
          </button>
        </div>
      </div>
    </div>
  </aside>
</template>
