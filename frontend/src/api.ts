import axios from 'axios'
import type { AuthUser } from './types'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000/api/v1/subscription',
})

export const tokenKey = 'argo_token'
export const userKey = 'argo_user'

api.interceptors.request.use(config => {
  const token = localStorage.getItem(tokenKey)
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  response => response,
  error => {
    if (error?.response?.status === 401 && !String(error?.config?.url ?? '').includes('/auth/login')) {
      localStorage.removeItem(tokenKey)
      localStorage.removeItem(userKey)
      if (window.location.pathname !== '/login') window.location.replace('/login')
    }
    return Promise.reject(error)
  },
)

export function saveSession(token: string, user: AuthUser) {
  localStorage.setItem(tokenKey, token)
  localStorage.setItem(userKey, JSON.stringify(user))
}

export function clearSession() {
  localStorage.removeItem(tokenKey)
  localStorage.removeItem(userKey)
}

export function readUser(): AuthUser | null {
  try {
    const value = localStorage.getItem(userKey)
    if (!value) return null
    const parsed = JSON.parse(value) as Partial<AuthUser> & Pick<AuthUser, 'id' | 'name' | 'email' | 'scopes'>
    const scopes = Array.isArray(parsed.scopes) ? parsed.scopes : []
    const role = parsed.role ?? (scopes.includes('subscription:admin') ? 'org_admin' : 'user')
    return { ...parsed, scopes, role }
  } catch {
    clearSession()
    return null
  }
}

export function requestKey() {
  return crypto.randomUUID()
}

export function apiMessage(error: unknown, fallback = 'The request could not be completed.') {
  if (axios.isAxiosError(error)) {
    const body = error.response?.data as { error?: { message?: string; details?: Array<{ msg?: string }> } } | undefined
    const detail = body?.error?.details?.[0]?.msg
    return detail || body?.error?.message || fallback
  }
  return fallback
}
