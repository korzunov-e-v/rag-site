import type { User } from '../types/auth'

const TOKEN_KEY = 'rag_access_token'
const USER_KEY = 'rag_user'

let token: string | null = localStorage.getItem(TOKEN_KEY)

let user: User | null = loadUser()

function loadUser(): User | null {
  const raw = localStorage.getItem(USER_KEY)

  if (!raw) {
    return null
  }

  try {
    return JSON.parse(raw) as User
  } catch {
    localStorage.removeItem(USER_KEY)
    return null
  }
}

export function getToken(): string | null {
  return token
}

export function getUser(): User | null {
  return user
}

export function setAuth(
  accessToken: string,
  currentUser: User,
): void {
  token = accessToken
  user = currentUser

  localStorage.setItem(TOKEN_KEY, accessToken)
  localStorage.setItem(USER_KEY, JSON.stringify(currentUser))
}

export function clearAuth(): void {
  token = null
  user = null

  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function isAuthenticated(): boolean {
  return token !== null
}
