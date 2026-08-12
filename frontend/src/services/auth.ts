import type { User } from '../types/auth'

const ACCESS_TOKEN_KEY = 'rag_access_token'
const REFRESH_TOKEN_KEY = 'rag_refresh_token'
const USER_KEY = 'rag_user'

let accessToken: string | null =
  localStorage.getItem(ACCESS_TOKEN_KEY)

let refreshToken: string | null =
  localStorage.getItem(REFRESH_TOKEN_KEY)

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
  return accessToken
}

export function getRefreshToken(): string | null {
  return refreshToken
}

export function getUser(): User | null {
  return user
}

export function setAuth(
  newAccessToken: string,
  newRefreshToken: string,
  currentUser: User,
): void {
  accessToken = newAccessToken
  refreshToken = newRefreshToken
  user = currentUser

  localStorage.setItem(
    ACCESS_TOKEN_KEY,
    newAccessToken,
  )

  localStorage.setItem(
    REFRESH_TOKEN_KEY,
    newRefreshToken,
  )

  localStorage.setItem(
    USER_KEY,
    JSON.stringify(currentUser),
  )
}

export function setAccessToken(
  newAccessToken: string,
): void {
  accessToken = newAccessToken

  localStorage.setItem(
    ACCESS_TOKEN_KEY,
    newAccessToken,
  )
}

export function clearAuth(): void {
  accessToken = null
  refreshToken = null
  user = null

  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function isAuthenticated(): boolean {
  return accessToken !== null
}
