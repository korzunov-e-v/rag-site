import type {
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  User,
} from '../types/auth'

async function handleResponse<T>(response: Response): Promise<T> {
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
    // Если backend не вернул JSON — оставляем стандартную ошибку.
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

export async function getMe(token: string): Promise<User> {
  const response = await fetch('/api/v1/auth/me', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  return handleResponse<User>(response)
}
