/**
 * CloudLens 认证工具
 * 前端不再保存密码或伪 Token，统一走后端真实认证。
 */

export interface AuthUser {
  username: string
  role?: string
  email?: string | null
}

interface LoginResponse {
  user: AuthUser
  expires_in: number
}

const AUTH_USER_KEY = "cloudlens_auth_user"

function getAuthApiBase(): string {
  if (typeof window === "undefined") {
    return "http://127.0.0.1:8000/api/auth"
  }

  const hostname = window.location.hostname
  const isLocalDev = hostname === "localhost" || hostname === "127.0.0.1"
  return isLocalDev ? "http://localhost:8000/api/auth" : `${window.location.origin}/api/auth`
}

function saveUser(user: AuthUser | null): void {
  if (typeof window === "undefined") return
  if (!user) {
    localStorage.removeItem(AUTH_USER_KEY)
    return
  }
  localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user))
}

function clearStoredAuth(): void {
  if (typeof window === "undefined") return
  localStorage.removeItem(AUTH_USER_KEY)
}

async function requestAuth<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${getAuthApiBase()}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData?.detail || errorData?.message || "认证请求失败")
  }

  return res.json()
}

/**
 * 登录验证
 */
export async function login(username: string, password: string): Promise<AuthUser | null> {
  try {
    const result = await requestAuth<LoginResponse>("/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    })
    saveUser(result.user)
    return result.user
  } catch {
    clearStoredAuth()
    return null
  }
}

/**
 * 登出
 */
export async function logout(): Promise<void> {
  try {
    await requestAuth("/logout", { method: "POST" })
  } catch {
    // 即使后端退出失败，也继续清理本地状态
  } finally {
    clearStoredAuth()
  }
}

/**
 * 获取当前用户（优先向后端确认）
 */
export async function fetchCurrentUser(): Promise<AuthUser | null> {
  try {
    const user = await requestAuth<AuthUser>("/me", { method: "GET" })
    saveUser(user)
    return user
  } catch {
    clearStoredAuth()
    return null
  }
}

/**
 * 检查是否已登录
 */
export async function isAuthenticated(): Promise<boolean> {
  const user = await fetchCurrentUser()
  return Boolean(user)
}

/**
 * 从本地缓存读取当前用户（仅用于快速展示）
 */
export function getCurrentUser(): AuthUser | null {
  if (typeof window === "undefined") return null

  const userStr = localStorage.getItem(AUTH_USER_KEY)
  if (!userStr) return null

  try {
    return JSON.parse(userStr) as AuthUser
  } catch {
    return null
  }
}
