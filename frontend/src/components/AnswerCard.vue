<script setup lang="ts">
import type { Answer } from '../types/ask'
function highlightQuote(text: string, quote: string) {
  if (!quote) {
    return [{ text, highlighted: false }]
  }

  const index = text.indexOf(quote)

  if (index === -1) {
    return [{ text, highlighted: false }]
  }

  return [
    {
      text: text.slice(0, index),
      highlighted: false,
    },
    {
      text: quote,
      highlighted: true,
    },
    {
      text: text.slice(index + quote.length),
      highlighted: false,
    },
  ].filter((part) => part.text)
}
defineProps<{
  answer: Answer
}>()
</script>

<template>
  <article
    class="rounded-2xl border border-slate-200 bg-white p-6
           shadow-sm transition hover:shadow-md"
  >
    <div class="flex items-start justify-between gap-4">
      <div class="min-w-0">
        <div class="flex items-center gap-2">
          <span class="text-lg">📄</span>

          <h3
            class="truncate font-medium text-slate-900"
            :title="answer.filename"
          >
            {{ answer.filename }}
          </h3>
        </div>
      </div>

      <div
        class="shrink-0 rounded-lg bg-slate-100 px-2.5 py-1
               text-xs font-medium text-slate-500"
        title="Чем меньше значение, тем ближе документ к запросу"
      >
        Distance {{ answer.distance.toFixed(3) }}
      </div>
    </div>

    <div class="mt-5">
      <p class="text-xs font-medium uppercase tracking-wide text-slate-400">
        Ответ
      </p>

      <p
        class="mt-2 whitespace-pre-line text-[15px] leading-7 text-slate-700"
      >
        {{ answer.answer }}
      </p>
    </div>

    <div
      v-if="answer.sources.length > 0"
      class="mt-6 border-t border-slate-100 pt-5"
    >
      <p
        class="mb-3 text-xs font-medium uppercase tracking-wide
               text-slate-400"
      >
        Источники
      </p>

      <div class="space-y-3">
        <div
          v-for="(source, index) in answer.sources"
          :key="source.chunk_id"
          class="rounded-xl bg-slate-50 p-4"
        >
          <div class="mb-2 flex items-center justify-between">
            <span class="text-xs font-medium text-slate-400">
              Источник {{ index + 1 }}
            </span>

            <span class="text-xs text-slate-400">
              {{ source.distance.toFixed(3) }}
            </span>
          </div>

          <p class="whitespace-pre-line text-sm leading-6 text-slate-600">
  «<template
    v-for="(part, partIndex) in highlightQuote(source.text, source.quote)"
    :key="partIndex"
  ><mark
      v-if="part.highlighted"
      class="rounded bg-yellow-200 px-0.5 text-slate-900"
    >{{ part.text }}</mark><template v-else>{{ part.text }}</template></template>»
</p>
        </div>
      </div>
    </div>
  </article>
</template>
