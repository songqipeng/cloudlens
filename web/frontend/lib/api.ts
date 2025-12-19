/**
 * API 请求工具（增强版）
 * 自动在所有请求中包含当前选中的账号参数
 * 支持重试、超时、请求去重
 */

const API_BASE = "http://127.0.0.1:8000/api"

// 请求去重Map
const pendingRequests = new Map<string, Promise<any>>()

/**
 * API错误类
 */
export class ApiError extends Error {
    constructor(
        public status: number,
        public detail: any,
        message?: string
    ) {
        super(message || detail?.error || detail?.detail || `API请求失败: ${status}`)
        this.name = "ApiError"
    }
}

/**
 * 获取当前选中的账号（从 localStorage）
 */
function getCurrentAccount(): string | null {
    if (typeof window === "undefined") return null
    // 优先从 URL 推断（/a/{account}/...），避免 localStorage 旧值导致请求打到错误租户
    const pathname = window.location.pathname || ""
    if (pathname.startsWith("/a/")) {
        const parts = pathname.split("/").filter(Boolean) // ["a", "{account}", ...]
        if (parts.length >= 2 && parts[0] === "a" && parts[1]) {
            try {
                return decodeURIComponent(parts[1])
            } catch {
                return parts[1]
            }
        }
    }
    return localStorage.getItem("currentAccount")
}

/**
 * 获取当前语言设置（从 localStorage）
 */
function getCurrentLocale(): string {
    if (typeof window === "undefined") return "zh"
    // 使用与 LocaleContext 相同的 key
    return localStorage.getItem("cloudlens_locale") || "zh"
}

/**
 * 构建带账号参数的 URL
 */
function buildUrl(endpoint: string, params?: Record<string, any>): string {
    const url = new URL(`${API_BASE}${endpoint}`, window.location.origin)
    
    // 添加账号参数 - 优先使用 params 中的 account，否则从 localStorage 获取
    const account = params?.account || getCurrentAccount()
    if (account) {
        url.searchParams.set("account", account)
        console.log(`[API] ${endpoint} - 使用账号: ${account}`)
    } else {
        console.warn(`[API] ${endpoint} - 未找到账号参数`)
    }
    
    // 添加语言参数
    const locale = params?.locale || getCurrentLocale()
    if (locale) {
        url.searchParams.set("locale", locale)
    }
    
    // 添加其他参数
    if (params) {
        Object.entries(params).forEach(([key, value]) => {
            if (key !== "account" && key !== "locale" && value !== undefined && value !== null) {
                url.searchParams.set(key, String(value))
            }
        })
    }
    
    return url.toString()
}

/**
 * GET 请求（增强版：支持重试、超时、请求去重）
 */
export async function apiGet<T = any>(
    endpoint: string, 
    params?: Record<string, any>,
    options?: RequestInit & { 
        retries?: number
        timeout?: number
        skipDedupe?: boolean
    }
): Promise<T> {
    const url = buildUrl(endpoint, params)
    const requestKey = `${options?.method || 'GET'}:${url}`
    
    // 请求去重
    if (!options?.skipDedupe && pendingRequests.has(requestKey)) {
        return pendingRequests.get(requestKey)!
    }
    
    const retries = options?.retries ?? 3
    const timeout = options?.timeout ?? 30000
    
    const requestPromise = (async () => {
        for (let i = 0; i < retries; i++) {
            try {
                const controller = new AbortController()
                const timeoutId = setTimeout(() => controller.abort(), timeout)
                
                const res = await fetch(url, { 
                    ...options, 
                    signal: controller.signal 
                })
                clearTimeout(timeoutId)
                
                if (!res.ok) {
                    const errorData = await res.json().catch(() => ({}))
                    const errorMessage = errorData?.detail || errorData?.error || errorData?.message || `API请求失败: ${res.status} ${res.statusText}`
                    console.error(`[API Error] ${res.status} ${res.statusText}: ${url}`, errorData)
                    throw new ApiError(res.status, errorData, `${errorMessage} (${url})`)
                }
                
                const data = await res.json()
                pendingRequests.delete(requestKey)
                return data
            } catch (error) {
                // 如果是 AbortError（超时），在最后一次重试前不重试
                if (error instanceof Error && error.name === 'AbortError') {
                    if (i === retries - 1) {
                        pendingRequests.delete(requestKey)
                        throw new ApiError(408, { error: '请求超时，请稍后重试' }, '请求超时')
                    }
                    // 超时错误也进行重试
                } else if (i === retries - 1) {
                    pendingRequests.delete(requestKey)
                    if (error instanceof ApiError) {
                        throw error
                    }
                    throw new ApiError(500, { error: String(error) })
                }
                // 指数退避重试
                await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, i)))
            }
        }
    })()
    
    if (!options?.skipDedupe) {
        pendingRequests.set(requestKey, requestPromise)
    }
    
    return requestPromise
}

/**
 * POST 请求（增强版）
 */
export async function apiPost<T = any>(
    endpoint: string,
    data?: any,
    params?: Record<string, any>,
    options?: RequestInit & { 
        retries?: number
        timeout?: number
    }
): Promise<T> {
    const url = buildUrl(endpoint, params)
    const retries = options?.retries ?? 1  // POST默认不重试
    const timeout = options?.timeout ?? 30000
    
    for (let i = 0; i < retries; i++) {
        try {
            const controller = new AbortController()
            const timeoutId = setTimeout(() => controller.abort(), timeout)
            
            const res = await fetch(url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    ...options?.headers,
                },
                body: data ? JSON.stringify(data) : undefined,
                ...options,
                signal: controller.signal,
            })
            clearTimeout(timeoutId)
            
            if (!res.ok) {
                const errorData = await res.json().catch(() => ({}))
                const errorMessage = errorData?.detail || errorData?.error || errorData?.message || `API请求失败: ${res.status} ${res.statusText}`
                console.error(`[API Error] ${res.status} ${res.statusText}: ${url}`, errorData)
                throw new ApiError(res.status, errorData, `${errorMessage} (${url})`)
            }
            
            return await res.json()
        } catch (error) {
            if (i === retries - 1) {
                if (error instanceof ApiError) {
                    throw error
                }
                throw new ApiError(500, { error: String(error) })
            }
            await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)))
        }
    }
    throw new ApiError(500, { error: "Request failed after retries" })
}

/**
 * PUT 请求（增强版）
 */
export async function apiPut<T = any>(
    endpoint: string,
    data?: any,
    params?: Record<string, any>,
    options?: RequestInit & { 
        retries?: number
        timeout?: number
    }
): Promise<T> {
    const url = buildUrl(endpoint, params)
    const retries = options?.retries ?? 1  // PUT默认不重试
    const timeout = options?.timeout ?? 30000
    
    for (let i = 0; i < retries; i++) {
        try {
            const controller = new AbortController()
            const timeoutId = setTimeout(() => controller.abort(), timeout)
            
            const res = await fetch(url, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    ...options?.headers,
                },
                body: data ? JSON.stringify(data) : undefined,
                ...options,
                signal: controller.signal,
            })
            clearTimeout(timeoutId)
            
            if (!res.ok) {
                const errorData = await res.json().catch(() => ({}))
                const errorMessage = errorData?.detail || errorData?.error || errorData?.message || `API请求失败: ${res.status} ${res.statusText}`
                console.error(`[API Error] ${res.status} ${res.statusText}: ${url}`, errorData)
                throw new ApiError(res.status, errorData, `${errorMessage} (${url})`)
            }
            
            return await res.json()
        } catch (error) {
            if (i === retries - 1) {
                if (error instanceof ApiError) {
                    throw error
                }
                throw new ApiError(500, { error: String(error) })
            }
            await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)))
        }
    }
    throw new ApiError(500, { error: "Request failed after retries" })
}

/**
 * DELETE 请求（增强版）
 */
export async function apiDelete<T = any>(
    endpoint: string,
    params?: Record<string, any>,
    options?: RequestInit & { 
        retries?: number
        timeout?: number
    }
): Promise<T> {
    const url = buildUrl(endpoint, params)
    const retries = options?.retries ?? 1  // DELETE默认不重试
    const timeout = options?.timeout ?? 30000
    
    for (let i = 0; i < retries; i++) {
        try {
            const controller = new AbortController()
            const timeoutId = setTimeout(() => controller.abort(), timeout)
            
            const res = await fetch(url, {
                method: "DELETE",
                ...options,
                signal: controller.signal,
            })
            clearTimeout(timeoutId)
            
            if (!res.ok) {
                const errorData = await res.json().catch(() => ({}))
                const errorMessage = errorData?.detail || errorData?.error || errorData?.message || `API请求失败: ${res.status} ${res.statusText}`
                console.error(`[API Error] ${res.status} ${res.statusText}: ${url}`, errorData)
                throw new ApiError(res.status, errorData, `${errorMessage} (${url})`)
            }
            
            return await res.json()
        } catch (error) {
            if (i === retries - 1) {
                if (error instanceof ApiError) {
                    throw error
                }
                throw new ApiError(500, { error: String(error) })
            }
            await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)))
        }
    }
    throw new ApiError(500, { error: "Request failed after retries" })
}







