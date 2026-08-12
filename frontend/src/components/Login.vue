<script setup lang="ts">
import {ref} from 'vue'
import {login, register} from '../api/auth'
import {setAuth} from '../services/auth'
import {connectSocket} from '../services/socket'

const emit = defineEmits<{
  authenticated: []
}>()

const email = ref('')
const password = ref('')

const isRegister = ref(false)
const loading = ref(false)
const error = ref<string | null>(null)

async function submit() {
  const emailValue = email.value.trim()
  const passwordValue = password.value

  if (!emailValue || !passwordValue) {
    error.value = 'Введите email и пароль'
    return
  }

  try {
    loading.value = true
    error.value = null

    const response = isRegister.value
        ? await register({
          email: emailValue,
          password: passwordValue,
        })
        : await login({
          email: emailValue,
          password: passwordValue,
        })

    setAuth(
        response.access_token,
        response.refresh_token,
        response.user,
    )

    connectSocket()

    emit('authenticated')
  } catch (err) {
    error.value = err instanceof Error
        ? err.message
        : 'Не удалось выполнить авторизацию'
  } finally {
    loading.value = false
  }
}

function toggleMode() {
  isRegister.value = !isRegister.value
  error.value = null
}
</script>

<template>
  <main
      class="flex min-h-screen items-center justify-center
           bg-slate-50 px-4"
  >
    <section
        class="w-full max-w-md rounded-2xl border
             border-slate-200 bg-white p-8 shadow-sm"
    >
      <div class="mb-8">
        <h1 class="text-2xl font-semibold text-slate-900">
          RAG
        </h1>

        <p class="mt-2 text-sm text-slate-500">
          {{
            isRegister
                ? 'Создайте аккаунт'
                : 'Войдите в аккаунт'
          }}
        </p>
      </div>

      <form
          class="space-y-4"
          @submit.prevent="submit"
      >
        <div>
          <label
              for="email"
              class="mb-1 block text-sm font-medium text-slate-700"
          >
            Email
          </label>

          <input
              id="email"
              v-model="email"
              type="email"
              autocomplete="email"
              class="w-full rounded-xl border border-slate-300
                   px-3 py-2.5 text-sm outline-none
                   focus:border-purple-500 focus:ring-2
                   focus:ring-purple-100"
              placeholder="you@example.com"
          />
        </div>

        <div>
          <label
              for="password"
              class="mb-1 block text-sm font-medium text-slate-700"
          >
            Пароль
          </label>

          <input
              id="password"
              v-model="password"
              type="password"
              :autocomplete="isRegister
              ? 'new-password'
              : 'current-password'"
              class="w-full rounded-xl border border-slate-300
                   px-3 py-2.5 text-sm outline-none
                   focus:border-purple-500 focus:ring-2
                   focus:ring-purple-100"
              placeholder="••••••••"
          />
        </div>

        <div
            v-if="error"
            class="rounded-xl border border-red-200
                 bg-red-50 p-3 text-sm text-red-700"
        >
          {{ error }}
        </div>

        <button
            type="submit"
            :disabled="loading"
            class="w-full rounded-xl bg-purple-600
                 px-4 py-2.5 text-sm font-medium
                 text-white transition
                 hover:bg-purple-700
                 disabled:cursor-not-allowed
                 disabled:opacity-50"
        >
          {{
            loading
                ? 'Подождите...'
                : isRegister
                    ? 'Зарегистрироваться'
                    : 'Войти'
          }}
        </button>
      </form>

      <button
          type="button"
          class="mt-5 w-full text-sm text-slate-500
               hover:text-purple-600"
          @click="toggleMode"
      >
        {{
          isRegister
              ? 'Уже есть аккаунт? Войти'
              : 'Нет аккаунта? Зарегистрироваться'
        }}
      </button>
    </section>
  </main>
</template>
