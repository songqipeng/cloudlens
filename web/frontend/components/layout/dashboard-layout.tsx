"use client"

import { ReactNode } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { 
    LayoutDashboard, 
    Server, 
    DollarSign, 
    Shield, 
    TrendingUp, 
    FileText, 
    Settings,
    BarChart3,
    Percent
} from "lucide-react"
import { AccountSelector } from "@/components/account-selector"
import { useAccount } from "@/contexts/account-context"

const navItems = [
    { href: "/", label: "Dashboard", icon: LayoutDashboard },
    { href: "/resources", label: "Resources", icon: Server },
    { href: "/cost", label: "Cost Analysis", icon: DollarSign },
    { href: "/discounts", label: "折扣分析", icon: Percent },
    { href: "/security", label: "Security", icon: Shield },
    { href: "/optimization", label: "Optimization", icon: TrendingUp },
    { href: "/reports", label: "Reports", icon: FileText },
    { href: "/settings", label: "Settings", icon: Settings },
]

interface DashboardLayoutProps {
    children: ReactNode
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
    const pathname = usePathname()
    const { currentAccount } = useAccount()

    // currentAccount 可能在首次渲染时还没从 /a/[account]/layout 同步进来
    // 优先从 URL 推断，避免侧边栏链接瞬间指向旧路由
    const accountFromPath = (() => {
        if (!pathname?.startsWith("/a/")) return null
        const parts = pathname.split("/").filter(Boolean) // ["a", "{account}", ...]
        if (parts.length >= 2 && parts[0] === "a" && parts[1]) return decodeURIComponent(parts[1])
        return null
    })()

    const effectiveAccount = currentAccount || accountFromPath
    const base = effectiveAccount ? `/a/${encodeURIComponent(effectiveAccount)}` : ""
    const accountHref = (href: string) => {
        if (!base) return href
        if (href === "/") return base
        return `${base}${href}`
    }
    
    return (
        <div className="min-h-screen bg-gradient-to-br from-background via-background to-zinc-950 text-foreground font-sans">
            {/* Sidebar */}
            <aside className="fixed left-0 top-0 w-72 h-screen border-r border-border/50 bg-gradient-to-b from-card/95 via-card/90 to-card/95 backdrop-blur-xl hidden lg:block z-40 overflow-y-auto shadow-2xl">
                <div className="p-6 h-full flex flex-col">
                    {/* Logo */}
                    <div className="mb-6 pb-6 border-b border-border/30">
                        <div className="flex items-center gap-3 mb-4">
                            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary via-blue-500 to-blue-600 flex items-center justify-center shadow-lg shadow-primary/40 ring-2 ring-primary/20">
                                <BarChart3 className="w-7 h-7 text-white" />
                            </div>
                            <div>
                                <h1 className="text-xl font-bold tracking-tight gradient-text">CloudLens</h1>
                                <p className="text-xs text-muted-foreground font-medium">多云资源治理平台</p>
                            </div>
                        </div>
                        {/* 账号选择器 */}
                        <AccountSelector />
                    </div>
                    
                    {/* Navigation */}
                    <nav className="space-y-1.5 flex-1 py-4">
                        {navItems.map(item => {
                            const Icon = item.icon
                            const href = accountHref(item.href)
                            const isActive = pathname === href ||
                                            (item.href !== "/" && pathname?.startsWith(href))
                            
                            return (
                                <Link
                                    key={item.href}
                                    href={href}
                                    className={`group relative flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-300 ${
                                        isActive
                                            ? "bg-gradient-to-r from-primary/15 to-primary/5 text-primary shadow-lg shadow-primary/10 border border-primary/30"
                                            : "text-muted-foreground hover:text-foreground hover:bg-muted/40 border border-transparent hover:border-border/50"
                                    }`}
                                >
                                    {isActive && (
                                        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-primary rounded-r-full"></div>
                                    )}
                                    <Icon className={`h-5 w-5 transition-all ${isActive ? 'scale-110 text-primary' : 'group-hover:scale-110 group-hover:text-foreground'}`} />
                                    <span className="flex-1">{item.label}</span>
                                    {isActive && (
                                        <div className="w-2 h-2 rounded-full bg-primary animate-pulse"></div>
                                    )}
                                </Link>
                            )
                        })}
                    </nav>
                    
                    {/* Footer */}
                    <div className="mt-auto pt-6 border-t border-border/30">
                        <div className="text-xs text-muted-foreground space-y-1">
                            <p className="font-semibold text-foreground">CloudLens v2.1</p>
                            <p className="opacity-70">企业级多云资源治理平台</p>
                        </div>
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="lg:ml-72 min-h-screen">
                {children}
            </main>
        </div>
    )
}





