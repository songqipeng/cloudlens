/**
 * CloudLens 简单认证工具
 * 用于前端登录验证和状态管理
 */

// 有效用户凭证
const VALID_CREDENTIALS = {
  username: 'demo',
  password: '123demo654'
}

// 存储键名
const AUTH_TOKEN_KEY = 'cloudlens_auth_token'
const AUTH_USER_KEY = 'cloudlens_auth_user'

// 简单的token生成（base64编码）
function generateToken(username: string): string {
  const payload = {
    username,
    exp: Date.now() + 7 * 24 * 60 * 60 * 1000, // 7天过期
    iat: Date.now()
  }
  return btoa(JSON.stringify(payload))
}

// 验证token是否有效
function verifyToken(token: string): { valid: boolean; username?: string } {
  try {
    const payload = JSON.parse(atob(token))
    if (payload.exp && payload.exp > Date.now()) {
      return { valid: true, username: payload.username }
    }
    return { valid: false }
  } catch {
    return { valid: false }
  }
}

/**
 * 登录验证
 */
export function login(username: string, password: string): boolean {
  if (username === VALID_CREDENTIALS.username && password === VALID_CREDENTIALS.password) {
    const token = generateToken(username)
    
    // 存储到localStorage
    if (typeof window !== 'undefined') {
      localStorage.setItem(AUTH_TOKEN_KEY, token)
      localStorage.setItem(AUTH_USER_KEY, JSON.stringify({ username }))
      
      // 同时设置cookie供middleware使用
      document.cookie = `${AUTH_TOKEN_KEY}=${token}; path=/; max-age=${7 * 24 * 60 * 60}; SameSite=Lax`
    }
    
    return true
  }
  return false
}

/**
 * 登出
 */
export function logout(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(AUTH_TOKEN_KEY)
    localStorage.removeItem(AUTH_USER_KEY)
    
    // 清除cookie
    document.cookie = `${AUTH_TOKEN_KEY}=; path=/; max-age=0`
  }
}

/**
 * 检查是否已登录
 */
export function isAuthenticated(): boolean {
  if (typeof window === 'undefined') return false
  
  const token = localStorage.getItem(AUTH_TOKEN_KEY)
  if (!token) return false
  
  const result = verifyToken(token)
  if (!result.valid) {
    // token无效，清理
    logout()
    return false
  }
  
  return true
}

/**
 * 获取当前用户
 */
export function getCurrentUser(): { username: string } | null {
  if (typeof window === 'undefined') return null
  
  const userStr = localStorage.getItem(AUTH_USER_KEY)
  if (!userStr) return null
  
  try {
    return JSON.parse(userStr)
  } catch {
    return null
  }
}

/**
 * 获取认证token
 */
export function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(AUTH_TOKEN_KEY)
}
