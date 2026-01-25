"use client"

import { ReactNode, useState } from "react"
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
    Percent,
    Wallet,
    Menu,
    X
} from "lucide-react"
import { AccountSelector } from "@/components/account-selector"
import { useAccount } from "@/contexts/account-context"
import { useLocale } from "@/contexts/locale-context"

interface DashboardLayoutProps {
    children: ReactNode
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
    const pathname = usePathname()
    const { currentAccount } = useAccount()
    const { t, locale } = useLocale()
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

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
    
    const navItems = [
        { href: "/", label: t.nav.dashboard, icon: LayoutDashboard },
        { href: "/resources", label: t.nav.resources, icon: Server },
        { href: "/cost", label: t.nav.costAnalysis, icon: DollarSign },
        { href: "/budgets", label: t.nav.budget, icon: Wallet },
        // { href: "/custom-dashboards", label: t.nav.customDashboards, icon: LayoutDashboard }, // 暂时屏蔽
        { href: "/discounts", label: t.nav.discountAnalysis, icon: Percent },
        { href: "/virtual-tags", label: t.nav.virtualTags, icon: BarChart3 },
        { href: "/security", label: t.nav.security, icon: Shield },
        { href: "/optimization", label: t.nav.optimization, icon: TrendingUp },
        { href: "/reports", label: t.nav.reports, icon: FileText },
        { href: "/settings", label: t.nav.settings, icon: Settings },
    ]
    
    return (
        <div className="min-h-screen bg-background text-foreground font-sans">
            {/* 移动端顶部导航栏 */}
            <header className="lg:hidden fixed top-0 left-0 right-0 h-14 bg-[rgba(15,15,20,0.95)] backdrop-blur-[20px] border-b border-[rgba(255,255,255,0.08)] z-50 flex items-center justify-between px-4">
                <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
                        <BarChart3 className="w-4 h-4 text-white" />
                    </div>
                    <span className="font-semibold text-foreground">CloudLens</span>
                </div>
                <button
                    onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                    className="p-2 rounded-lg hover:bg-[rgba(255,255,255,0.1)] transition-colors"
                    aria-label="Toggle menu"
                >
                    {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
                </button>
            </header>

            {/* 移动端抽屉式菜单 */}
            {mobileMenuOpen && (
                <div className="lg:hidden fixed inset-0 z-40">
                    {/* 背景遮罩 */}
                    <div 
                        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
                        onClick={() => setMobileMenuOpen(false)}
                    />
                    {/* 菜单内容 */}
                    <aside className="absolute top-14 left-0 right-0 bottom-0 bg-[rgba(15,15,20,0.98)] overflow-y-auto animate-fade-in">
                        <nav className="p-4 space-y-1">
                            {navItems.map(item => {
                                const Icon = item.icon
                                const href = accountHref(item.href)
                                const isActive = pathname === href ||
                                                (item.href !== "/" && pathname?.startsWith(href))
                                
                                return (
                                    <Link
                                        key={item.href}
                                        href={href}
                                        onClick={() => setMobileMenuOpen(false)}
                                        className={`group relative flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 ${
                                            isActive
                                                ? "bg-primary/15 text-primary border-l-2 border-l-primary"
                                                : "text-muted-foreground hover:text-foreground hover:bg-[rgba(255,255,255,0.05)]"
                                        }`}
                                    >
                                        <Icon className={`h-5 w-5 ${isActive ? "text-primary" : ""}`} />
                                        <span className="flex-1">{item.label}</span>
                                    </Link>
                                )
                            })}
                        </nav>
                        <div className="p-4 border-t border-[rgba(255,255,255,0.08)]">
                            <AccountSelector />
                        </div>
                    </aside>
                </div>
            )}

            {/* Finout 风格侧边栏 - 仅桌面端显示 */}
            <aside className="fixed left-0 top-0 w-72 h-screen border-r border-[rgba(255,255,255,0.08)] bg-[rgba(15,15,20,0.95)] backdrop-blur-[20px] hidden lg:block z-40 overflow-y-auto">
                <div className="p-6 h-full flex flex-col">
                    {/* Logo - Finout 风格：简洁 */}
                    <div className="mb-6 pb-6 border-b border-[rgba(255,255,255,0.08)]">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center">
                                <BarChart3 className="w-5 h-5 text-white" />
                            </div>
                            <div className="flex-1 min-w-0">
                                <h1 className="text-lg font-bold tracking-tight text-foreground">CloudLens</h1>
                                <p className="text-xs text-muted-foreground truncate">{locale === 'zh' ? '多云资源治理平台' : 'Multi-Cloud Resource Governance Platform'}</p>
                            </div>
                        </div>
                    </div>
                    
                    {/* Navigation - Finout 风格：简洁清晰 */}
                    <nav className="space-y-1 flex-1 py-4">
                        {navItems.map(item => {
                            const Icon = item.icon
                            const href = accountHref(item.href)
                            const isActive = pathname === href ||
                                            (item.href !== "/" && pathname?.startsWith(href))
                            
                            return (
                                <Link
                                    key={item.href}
                                    href={href}
                                    className={`group relative flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                                        isActive
                                            ? "bg-primary/15 text-primary border-l-2 border-l-primary"
                                            : "text-muted-foreground hover:text-foreground hover:bg-[rgba(255,255,255,0.05)]"
                                    }`}
                                >
                                    <Icon className={`h-4 w-4 ${isActive ? "text-primary" : ""}`} />
                                    <span className="flex-1">{item.label}</span>
                                </Link>
                            )
                        })}
                    </nav>
                    
                    {/* Footer - Finout 风格：简洁 */}
                    <div className="mt-auto pt-6 border-t border-[rgba(255,255,255,0.08)]">
                        {/* 账号选择器 - 移到底部 */}
                        <AccountSelector />
                    </div>
                </div>
            </aside>

            {/* Main Content - Finout 风格：更大的内容区域 */}
            <main className="lg:ml-72 min-h-screen pt-14 lg:pt-0">
                {children}
            </main>
        </div>
    )
}






