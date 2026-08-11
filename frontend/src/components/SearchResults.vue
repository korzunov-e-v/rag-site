<script setup lang="ts">
import AnswerCard from './AnswerCard.vue'
import type { Answer } from '../types/ask'

defineProps<{
  answers: Answer[]
}>()
</script>

<template>
  <div class="space-y-4">
    <AnswerCard
      v-for="answer in answers"
      :key="answer.document_id"
      :answer="answer"
    />
  </div>
</template>
