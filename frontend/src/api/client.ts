import {
  clearAuth,
  getRefreshToken,
  getToken,
  setAuth,
} from '../services/auth'
import { refresh } from './auth'

let refreshPromise: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken()

  if (!refreshToken) {
    clearAuth()
    return null
  }

  if (!refreshPromise) {
    refreshPromise = refresh({
      refresh_token: refreshToken,
    })
      .then((response) => {
        setAuth(
          response.access_token,
          response.refresh_token,
          response.user,
        )

        return response.access_token
      })
      .catch(() => {
        clearAuth()
        return null
      })
      .finally(() => {
        refreshPromise = null
      })
  }

  return refreshPromise
}

export async function apiFetch(
  input: RequestInfo | URL,
  init: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(init.headers)

  const token = getToken()

  if (token) {
    headers.set(
      'Authorization',
      `Bearer ${token}`,
    )
  }

  let response = await fetch(input, {
    ...init,
    headers,
  })

  if (response.status !== 401) {
    return response
  }

  const newAccessToken = await refreshAccessToken()

  if (!newAccessToken) {
    return response
  }

  const retryHeaders = new Headers(init.headers)

  retryHeaders.set(
    'Authorization',
    `Bearer ${newAccessToken}`,
  )

  response = await fetch(input, {
    ...init,
    headers: retryHeaders,
  })

  return response
}
