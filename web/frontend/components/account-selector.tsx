"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { useAccount } from "@/contexts/account-context"
import { useLocale } from "@/contexts/locale-context"
import { Check, ChevronDown, Search, User, RefreshCw, Plus, Settings } from "lucide-react"

export function AccountSelector() {
    const { currentAccount, accounts, setCurrentAccount, refreshAccounts, loading } = useAccount()
    const { t } = useLocale()
    const router = useRouter()
    const pathname = usePathname()
    const [isOpen, setIsOpen] = useState(false)
    const [keyword, setKeyword] = useState("")
    const inputRef = useRef<HTMLInputElement>(null)

    const selectedAccount = accounts.find(acc => acc.name === currentAccount)

    const filtered = useMemo(() => {
        const k = keyword.trim().toLowerCase()
        if (!k) return accounts
        return accounts.filter(a =>
            a.name.toLowerCase().includes(k) ||
            a.region.toLowerCase().includes(k) ||
            a.access_key_id.toLowerCase().includes(k)
        )
    }, [accounts, keyword])

    useEffect(() => {
        if (!isOpen) return
        const t = window.setTimeout(() => inputRef.current?.focus(), 50)
        return () => window.clearTimeout(t)
    }, [isOpen])

    useEffect(() => {
        if (!isOpen) return
        const onKeyDown = (e: KeyboardEvent) => {
            if (e.key === "Escape") setIsOpen(false)
        }
        window.addEventListener("keydown", onKeyDown)
        return () => window.removeEventListener("keydown", onKeyDown)
    }, [isOpen])

    return (
        <div className="relative">
            <button
                onClick={() => setIsOpen(!isOpen)}
                aria-haspopup="menu"
                aria-expanded={isOpen}
                className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl border border-border/50 bg-background/70 backdrop-blur-sm hover:bg-muted/40 transition-all text-sm font-medium justify-between group shadow-sm hover:shadow-md"
            >
                <div className="flex items-center gap-3 flex-1 min-w-0">
                    <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary/20 via-cyan-500/15 to-primary/10 ring-1 ring-border/60 flex items-center justify-center flex-shrink-0">
                        <User className="w-4 h-4 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0 text-left">
                        <div className="text-[11px] text-muted-foreground leading-none mb-1">{t.locale === 'zh' ? '当前账号' : 'Current Account'}</div>
                        <div className="font-semibold text-foreground truncate leading-snug">
                            {selectedAccount ? selectedAccount.name : (t.locale === 'zh' ? '请选择账号' : 'Select Account')}
                        </div>
                        {selectedAccount?.region && (
                            <div className="text-[11px] text-muted-foreground/90 truncate mt-0.5">
                                {selectedAccount.region}
                            </div>
                        )}
                    </div>
                </div>
                <ChevronDown className={`w-4 h-4 text-muted-foreground transition-transform flex-shrink-0 ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            {isOpen && (
                <>
                    <div 
                        className="fixed inset-0 z-40" 
                        onClick={() => setIsOpen(false)}
                    />
                    <div className="absolute top-full left-0 mt-2 w-[360px] bg-background/95 backdrop-blur-xl border border-border/60 rounded-2xl shadow-2xl z-50 overflow-hidden">
                        <div className="p-4 border-b border-border/50 bg-gradient-to-r from-primary/8 via-cyan-500/8 to-primary/8">
                            <div className="flex items-center justify-between gap-3">
                                <div className="min-w-0">
                                    <div className="text-sm font-semibold text-foreground leading-snug">{t.locale === 'zh' ? '账号' : 'Account'}</div>
                                    <div className="text-[11px] text-muted-foreground mt-0.5 truncate">
                                        {t.locale === 'zh' ? '当前：' : 'Current: '}<span className="font-medium text-foreground">{selectedAccount?.name || (t.locale === 'zh' ? '未选择' : 'Not Selected')}</span>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    <Link
                                        href={currentAccount ? `/a/${encodeURIComponent(currentAccount)}/settings/accounts` : "/settings/accounts"}
                                        onClick={() => setIsOpen(false)}
                                        className="p-2 rounded-xl hover:bg-muted/50 transition-colors text-muted-foreground hover:text-foreground"
                                        title="账号管理"
                                    >
                                        <Settings className="w-4 h-4" />
                                    </Link>
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation()
                                            refreshAccounts()
                                        }}
                                        className="p-2 rounded-xl hover:bg-muted/50 transition-colors text-muted-foreground hover:text-foreground"
                                        title="刷新账号列表"
                                    >
                                        <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                                    </button>
                                </div>
                            </div>
                            <div className="mt-3 relative">
                                <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                                <input
                                    ref={inputRef}
                                    value={keyword}
                                    onChange={(e) => setKeyword(e.target.value)}
                                    placeholder="搜索账号 / 区域 / AccessKey..."
                                    className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-border/60 bg-background/70 focus:outline-none focus:ring-2 focus:ring-primary/30 text-sm"
                                />
                            </div>
                        </div>

                        <div className="max-h-80 overflow-y-auto">
                            {accounts.length === 0 ? (
                                <div className="p-6 text-center">
                                    <div className="text-sm text-muted-foreground mb-3">暂无账号</div>
                                    <Link
                                        href="/settings/accounts"
                                        onClick={() => setIsOpen(false)}
                                        className="inline-flex items-center gap-2 px-4 py-2 text-sm bg-primary text-primary-foreground rounded-xl hover:bg-primary/90 transition-colors"
                                    >
                                        <Plus className="w-4 h-4" />
                                        添加账号
                                    </Link>
                                </div>
                            ) : filtered.length === 0 ? (
                                <div className="p-6 text-center">
                                    <div className="text-sm text-muted-foreground">未找到匹配账号</div>
                                    <button
                                        onClick={() => setKeyword("")}
                                        className="mt-3 px-4 py-2 text-sm rounded-xl border border-border/60 hover:bg-muted/40 transition-colors"
                                    >
                                        清空搜索
                                    </button>
                                </div>
                            ) : (
                                <>
                                    {filtered.map((account) => {
                                        const active = currentAccount === account.name
                                        return (
                                            <button
                                                key={account.name}
                                                onClick={() => {
                                                    console.log('[AccountSelector] 切换账号:', account.name)
                                                    setCurrentAccount(account.name)
                                                    setIsOpen(false)
                                                    setKeyword("")
                                                    // 路由分租户：保持当前子路径不变，仅替换账号段
                                                    const encoded = encodeURIComponent(account.name)
                                                    if (pathname?.startsWith("/a/")) {
                                                        const parts = pathname.split("/").filter(Boolean) // ["a", "{old}", ...]
                                                        if (parts.length >= 2 && parts[0] === "a") {
                                                            parts[1] = encoded
                                                            router.push("/" + parts.join("/"))
                                                            return
                                                        }
                                                    }
                                                    router.push(`/a/${encoded}`)
                                                }}
                                                className={`w-full px-4 py-3 text-left transition-all flex items-center justify-between border-b border-border/30 last:border-0 ${
                                                    active
                                                        ? 'bg-primary/10'
                                                        : 'hover:bg-muted/40'
                                                }`}
                                            >
                                                <div className="flex items-center gap-3 min-w-0">
                                                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ring-1 ${
                                                        active ? "bg-primary/15 ring-primary/30" : "bg-muted/40 ring-border/60"
                                                    }`}>
                                                        <User className={`w-4 h-4 ${active ? "text-primary" : "text-muted-foreground"}`} />
                                                    </div>
                                                    <div className="min-w-0">
                                                        <div className="font-semibold text-sm text-foreground truncate">{account.name}</div>
                                                        <div className="text-[11px] text-muted-foreground mt-0.5 truncate">
                                                            {account.region} · AK {account.access_key_id.substring(0, 8)}...
                                                        </div>
                                                    </div>
                                                </div>
                                                {active && (
                                                    <div className="flex items-center gap-2 flex-shrink-0">
                                                        <span className="text-[11px] text-primary/90 font-medium">当前</span>
                                                        <Check className="w-5 h-5 text-primary" />
                                                    </div>
                                                )}
                                            </button>
                                        )
                                    })}
                                    <div className="p-3 border-t border-border/50 bg-background/70">
                                        <Link
                                            href={currentAccount ? `/a/${encodeURIComponent(currentAccount)}/settings/accounts` : "/settings/accounts"}
                                            onClick={() => setIsOpen(false)}
                                            className="w-full px-3 py-2.5 rounded-xl hover:bg-muted/40 transition-colors flex items-center justify-center gap-2 text-sm text-primary border border-border/60"
                                        >
                                            <Plus className="w-4 h-4" />
                                            添加 / 管理账号
                                        </Link>
                                    </div>
                                </>
                            )}
                        </div>
                    </div>
                </>
            )}
        </div>
    )
}

// 兼容默认导入（有些地方可能会写成 `import AccountSelector from ...`）
export default AccountSelector







