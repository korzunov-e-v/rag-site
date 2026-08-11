<script setup lang="ts">
import type { Message } from '../types/chat'

defineProps<{
  message: Message
}>()
</script>

<template>
  <div
    class="flex"
    :class="message.role === 'user' ? 'justify-end' : 'justify-start'"
  >
    <div
      class="max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-6"
      :class="
        message.role === 'user'
          ? 'bg-purple-600 text-white'
          : 'bg-white text-slate-800 shadow-sm ring-1 ring-slate-200'
      "
    >
      {{ message.content }}
    </div>
  </div>
</template>
