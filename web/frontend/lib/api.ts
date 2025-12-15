/**
 * API 请求工具
 * 自动在所有请求中包含当前选中的账号参数
 */

const API_BASE = "http://127.0.0.1:8000/api"

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
    
    // 添加其他参数
    if (params) {
        Object.entries(params).forEach(([key, value]) => {
            if (key !== "account" && value !== undefined && value !== null) {
                url.searchParams.set(key, String(value))
            }
        })
    }
    
    return url.toString()
}

/**
 * GET 请求
 */
export async function apiGet<T = any>(
    endpoint: string, 
    params?: Record<string, any>,
    options?: RequestInit
): Promise<T> {
    const url = buildUrl(endpoint, params)
    const res = await fetch(url, options)
    if (!res.ok) {
        throw new Error(`API request failed: ${res.statusText}`)
    }
    return res.json()
}

/**
 * POST 请求
 */
export async function apiPost<T = any>(
    endpoint: string,
    data?: any,
    params?: Record<string, any>
): Promise<T> {
    const url = buildUrl(endpoint, params)
    const res = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: data ? JSON.stringify(data) : undefined,
    })
    if (!res.ok) {
        throw new Error(`API request failed: ${res.statusText}`)
    }
    return res.json()
}

/**
 * DELETE 请求
 */
export async function apiDelete<T = any>(
    endpoint: string,
    params?: Record<string, any>
): Promise<T> {
    const url = buildUrl(endpoint, params)
    const res = await fetch(url, {
        method: "DELETE",
    })
    if (!res.ok) {
        throw new Error(`API request failed: ${res.statusText}`)
    }
    return res.json()
}





