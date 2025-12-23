"use client"

import { createContext, useContext, useState, useEffect, ReactNode } from "react"

interface Account {
    name: string
    alias?: string  // 别名（可选）
    region: string
    access_key_id: string
}

interface AccountContextType {
    currentAccount: string | null
    accounts: Account[]
    setCurrentAccount: (account: string | null) => void
    refreshAccounts: () => Promise<void>
    loading: boolean
}

const AccountContext = createContext<AccountContextType | undefined>(undefined)

function getAccountFromPathname(): string | null {
    if (typeof window === "undefined") return null
    const pathname = window.location.pathname || ""
    if (!pathname.startsWith("/a/")) return null
    const parts = pathname.split("/").filter(Boolean) // ["a", "{account}", ...]
    if (parts.length >= 2 && parts[0] === "a" && parts[1]) {
        try {
            return decodeURIComponent(parts[1])
        } catch {
            return parts[1]
        }
    }
    return null
}

export function AccountProvider({ children }: { children: ReactNode }) {
    // 注意：这里不要在首次渲染就读取 window/localStorage 来决定渲染结果
    // 否则会导致 SSR HTML 与客户端首帧不一致（hydration failed）。
    // 账号解析放到 useEffect 中完成（AccountSync 也会在 /a/[account] 路由下同步账号）。
    const [currentAccount, setCurrentAccountState] = useState<string | null>(null)
    const [accounts, setAccounts] = useState<Account[]>([])
    const [loading, setLoading] = useState(true)

    // 首次挂载后，把 URL / localStorage 的选择同步到 state
    useEffect(() => {
        if (typeof window === "undefined") return
        const selected = getAccountFromPathname() || localStorage.getItem("currentAccount")
        if (selected) setCurrentAccountState(selected)
        // 仅做一次同步；后续以 AccountSync / setCurrentAccount 为准
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    // 获取账号列表
    const refreshAccounts = async () => {
        try {
            // 优先使用新的 /settings/accounts 接口（包含别名）
            let res = await fetch('http://127.0.0.1:8000/api/settings/accounts')
            if (!res.ok) {
                // 如果新接口失败，回退到旧接口
                res = await fetch('http://127.0.0.1:8000/api/accounts')
            }
            if (res.ok) {
                const response = await res.json()
                // 处理不同的响应格式
                const data = response.data || response
                setAccounts(data)
                
                // 注意：这里不要只依赖闭包里的 currentAccount（可能是旧值）
                // 优先读取 localStorage 中最新选择
                // 另外：如果当前路由就是 /a/{account}，也要优先信任路由参数
                const selected = (typeof window === "undefined")
                    ? currentAccount
                    : (getAccountFromPathname() || localStorage.getItem("currentAccount") || currentAccount)

                // 如果当前账号不在列表中，重置为第一个账号或 null
                if (selected && !data.find((acc: Account) => acc.name === selected)) {
                    if (data.length > 0) {
                        setCurrentAccountState(data[0].name)
                        localStorage.setItem("currentAccount", data[0].name)
                    } else {
                        setCurrentAccountState(null)
                        localStorage.removeItem("currentAccount")
                    }
                } else if (!selected && data.length > 0) {
                    // 如果没有选中账号，选择第一个
                    setCurrentAccountState(data[0].name)
                    localStorage.setItem("currentAccount", data[0].name)
                }
            }
        } catch (e) {
            console.error("Failed to fetch accounts:", e)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        refreshAccounts()
    }, [])

    const setCurrentAccount = (account: string | null) => {
        console.log('[AccountContext] 设置账号:', account)
        setCurrentAccountState(account)
        if (account) {
            localStorage.setItem("currentAccount", account)
            console.log('[AccountContext] 已保存到 localStorage:', localStorage.getItem("currentAccount"))
        } else {
            localStorage.removeItem("currentAccount")
        }
    }

    return (
        <AccountContext.Provider value={{
            currentAccount,
            accounts,
            setCurrentAccount,
            refreshAccounts,
            loading
        }}>
            {children}
        </AccountContext.Provider>
    )
}

export function useAccount() {
    const context = useContext(AccountContext)
    if (context === undefined) {
        throw new Error("useAccount must be used within AccountProvider")
    }
    return context
}










