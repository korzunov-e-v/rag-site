<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  disabled?: boolean
}>()

const emit = defineEmits<{
  submit: [query: string]
}>()

const query = ref('')

function submit() {
  const value = query.value.trim()

  if (!value) {
    return
  }

  emit('submit', value)
  query.value = ''
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    submit()
  }
}
</script>

<template>
  <div class="flex items-end gap-2 rounded-2xl border bg-white p-2 shadow-sm">
    <textarea
      v-model="query"
      rows="1"
      placeholder="Задайте вопрос..."
      class="max-h-40 min-h-10 flex-1 resize-none bg-transparent px-3 py-2
             text-sm outline-none placeholder:text-slate-400"
      :disabled="disabled"
      @keydown="handleKeydown"
    />

    <button
      type="button"
      class="rounded-xl bg-purple-600 px-4 py-2 text-sm font-medium
             text-white transition hover:bg-purple-700
             disabled:cursor-not-allowed disabled:opacity-50"
      :disabled="disabled || !query.trim()"
      @click="submit"
    >
      Отправить
    </button>
  </div>
</template>
