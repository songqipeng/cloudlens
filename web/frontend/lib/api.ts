/**
 * API 请求工具（增强版）
 * 自动在所有请求中包含当前选中的账号参数
 * 支持重试、超时、请求去重
 */

import { getTranslations } from "./i18n"
import type { Locale } from "./i18n"

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
        super(message || detail?.error || detail?.detail || `API request failed: ${status}`)
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
    // 确保 API_BASE 是绝对路径
    let baseUrl = API_BASE;
    if (!baseUrl.startsWith('http')) {
        baseUrl = new URL(baseUrl, window.location.origin).toString();
    }

    // 构建完整 URL
    let fullUrl = `${baseUrl}${endpoint}`;
    // 防止出现双斜杠（除了 protocol 后的）
    fullUrl = fullUrl.replace(/([^:])\/\//g, '$1/');

    const url = new URL(fullUrl);

    // 添加账号参数 - 优先使用 params 中的 account，否则从 localStorage 获取
    const account = params?.account || getCurrentAccount()
    if (account) {
        url.searchParams.set("account", account)
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

    const finalUrl = url.toString();
    console.log(`[API-DEBUG] ${endpoint} -> ${finalUrl}`);
    return finalUrl
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
        onTimeout?: (attempt: number, totalRetries: number) => void
    }
): Promise<T> {
    const url = buildUrl(endpoint, params)
    const requestKey = `${options?.method || 'GET'}:${url}`

    // 请求去重
    if (!options?.skipDedupe && pendingRequests.has(requestKey)) {
        console.log(`[API] 请求去重: ${endpoint}`)
        return pendingRequests.get(requestKey)!
    }

    const retries = options?.retries ?? 3
    const timeout = options?.timeout ?? 120000  // 默认超时时间增加到120秒（dashboard API 需要更长时间）

    const requestPromise = (async () => {
        let lastError: Error | null = null

        for (let i = 0; i < retries; i++) {
            try {
                const controller = new AbortController()
                const timeoutId = setTimeout(() => {
                    controller.abort()
                    if (options?.onTimeout) {
                        options.onTimeout(i + 1, retries)
                    }
                }, timeout)

                const res = await fetch(url, {
                    ...options,
                    signal: controller.signal
                })
                clearTimeout(timeoutId)

                if (!res.ok) {
                    const errorData = await res.json().catch(() => ({}))
                    const locale = getCurrentLocale() as Locale
                    const defaultMessage = locale === 'zh'
                        ? `API请求失败: ${res.status} ${res.statusText}`
                        : `API request failed: ${res.status} ${res.statusText}`
                    const errorMessage = errorData?.detail || errorData?.error || errorData?.message || defaultMessage
                    console.error(`[API Error] ${res.status} ${res.statusText}: ${url}`, errorData)

                    // 对于4xx错误，不重试
                    if (res.status >= 400 && res.status < 500 && res.status !== 408) {
                        pendingRequests.delete(requestKey)
                        throw new ApiError(res.status, errorData, `${errorMessage} (${url})`)
                    }

                    // 对于5xx和408错误，进行重试
                    lastError = new ApiError(res.status, errorData, `${errorMessage} (${url})`)
                    if (i === retries - 1) {
                        pendingRequests.delete(requestKey)
                        throw lastError
                    }
                    // 等待后重试
                    await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, i)))
                    continue
                }

                const data = await res.json()
                pendingRequests.delete(requestKey)
                return data
            } catch (error) {
                // 如果是 AbortError（超时）
                if (error instanceof Error && error.name === 'AbortError') {
                    lastError = error
                    const locale = getCurrentLocale() as Locale
                    const endpointName = endpoint.split('?')[0].split('/').pop() || endpoint
                    const waitedSeconds = Math.round(timeout / 1000)

                    if (i === retries - 1) {
                        // 最后一次重试失败
                        pendingRequests.delete(requestKey)
                        const timeoutMessage = locale === 'zh'
                            ? `请求超时 (${endpointName})，已等待 ${waitedSeconds} 秒。建议稍后重试或使用缓存数据。`
                            : `Request Timeout (${endpointName}), waited ${waitedSeconds}s. Please try again later or use cached data.`
                        console.warn(`[API] 请求超时（最终失败）: ${endpoint}`, { timeout, retries, waitedSeconds })
                        throw new ApiError(408, {
                            error: timeoutMessage,
                            endpoint,
                            timeout,
                            waitedSeconds,
                            suggestion: locale === 'zh'
                                ? '可以尝试使用缓存数据或稍后重试'
                                : 'Try using cached data or retry later'
                        }, timeoutMessage)
                    }

                    // 超时重试，增加等待时间
                    const waitTime = 2000 * Math.pow(2, i)
                    console.warn(`[API] 请求超时，正在重试 (${i + 1}/${retries}): ${endpoint}，等待 ${waitTime}ms`)
                    await new Promise(resolve => setTimeout(resolve, waitTime))
                    continue
                }

                // 其他错误
                if (error instanceof ApiError) {
                    lastError = error
                    // 对于4xx错误（除了408），不重试
                    if (error.status >= 400 && error.status < 500 && error.status !== 408) {
                        pendingRequests.delete(requestKey)
                        throw error
                    }
                } else {
                    lastError = error instanceof Error ? error : new Error(String(error))
                }

                // 最后一次重试失败
                if (i === retries - 1) {
                    pendingRequests.delete(requestKey)
                    if (error instanceof ApiError) {
                        throw error
                    }
                    throw new ApiError(500, { error: String(error) }, `Request failed: ${error}`)
                }

                // 指数退避重试
                const waitTime = 1000 * Math.pow(2, i)
                console.warn(`[API] 请求失败，正在重试 (${i + 1}/${retries}): ${endpoint}，等待 ${waitTime}ms`)
                await new Promise(resolve => setTimeout(resolve, waitTime))
            }
        }

        // 理论上不会到达这里，但为了类型安全
        pendingRequests.delete(requestKey)
        throw lastError || new ApiError(500, { error: "Request failed after retries" })
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
                const locale = getCurrentLocale() as Locale
                const defaultMessage = locale === 'zh'
                    ? `API请求失败: ${res.status} ${res.statusText}`
                    : `API request failed: ${res.status} ${res.statusText}`
                const errorMessage = errorData?.detail || errorData?.error || errorData?.message || defaultMessage
                console.error(`[API Error] ${res.status} ${res.statusText}: ${url}`, errorData)
                throw new ApiError(res.status, errorData, `${errorMessage} (${url})`)
            }

            return await res.json()
        } catch (error) {
            // 如果是 AbortError（超时），提供更友好的错误信息
            if (error instanceof Error && error.name === 'AbortError') {
                if (i === retries - 1) {
                    const locale = getCurrentLocale() as Locale
                    const endpointName = endpoint.split('?')[0].split('/').pop() || endpoint
                    const timeoutMessage = locale === 'zh'
                        ? `请求超时 (${endpointName})，已等待 ${Math.round(timeout / 1000)} 秒`
                        : `Request Timeout (${endpointName}), waited ${Math.round(timeout / 1000)}s`
                    console.warn(`[API] 请求超时: ${endpoint}`, { timeout, retries })
                    throw new ApiError(408, { error: timeoutMessage, endpoint, timeout }, timeoutMessage)
                }
                // 超时错误也进行重试，但增加等待时间
                console.warn(`[API] 请求超时，正在重试 (${i + 1}/${retries}): ${endpoint}`)
                await new Promise(resolve => setTimeout(resolve, 2000 * Math.pow(2, i)))
                continue
            } else if (i === retries - 1) {
                if (error instanceof ApiError) {
                    throw error
                }
                throw new ApiError(500, { error: String(error) })
            }
            // 指数退避重试
            await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, i)))
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
                const locale = getCurrentLocale() as Locale
                const defaultMessage = locale === 'zh'
                    ? `API请求失败: ${res.status} ${res.statusText}`
                    : `API request failed: ${res.status} ${res.statusText}`
                const errorMessage = errorData?.detail || errorData?.error || errorData?.message || defaultMessage
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
                const locale = getCurrentLocale() as Locale
                const defaultMessage = locale === 'zh'
                    ? `API请求失败: ${res.status} ${res.statusText}`
                    : `API request failed: ${res.status} ${res.statusText}`
                const errorMessage = errorData?.detail || errorData?.error || errorData?.message || defaultMessage
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








