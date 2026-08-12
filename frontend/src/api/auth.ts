import type {
  LoginRequest,
  RefreshRequest,
  RegisterRequest,
  TokenResponse,
  User,
} from '../types/auth'
import { apiFetch } from './client'

async function handleResponse<T>(
  response: Response,
): Promise<T> {
  if (response.ok) {
    return response.json()
  }

  let message = 'Произошла ошибка'

  try {
    const data = await response.json()

    if (typeof data.detail === 'string') {
      message = data.detail
    }
  } catch {
    // Если backend не вернул JSON —
    // оставляем стандартную ошибку.
  }

  throw new Error(message)
}

export async function login(
  data: LoginRequest,
): Promise<TokenResponse> {
  const response = await fetch('/api/v1/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  })

  return handleResponse<TokenResponse>(response)
}

export async function register(
  data: RegisterRequest,
): Promise<TokenResponse> {
  const response = await fetch('/api/v1/auth/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  })

  return handleResponse<TokenResponse>(response)
}

export async function refresh(
  data: RefreshRequest,
): Promise<TokenResponse> {
  const response = await fetch('/api/v1/auth/refresh', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  })

  return handleResponse<TokenResponse>(response)
}

export async function getMe(): Promise<User> {
  const response = await apiFetch('/api/v1/auth/me')

  return handleResponse<User>(response)
}
