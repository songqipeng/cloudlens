"use client"

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
    Wallet,
    Bell,
    PieChart,
    Sparkles
} from "lucide-react"

const navItems = [
    { href: "/", label: "Dashboard", icon: LayoutDashboard },
    { href: "/resources", label: "Resources", icon: Server },
    { href: "/cost", label: "Cost", icon: DollarSign },
    { href: "/budgets", label: "预算管理", icon: Wallet },
    { href: "/virtual-tags", label: "虚拟标签", icon: FileText },
    { href: "/alerts", label: "告警管理", icon: Bell },
    { href: "/cost-allocation", label: "成本分配", icon: PieChart },
    { href: "/ai-optimizer", label: "AI优化", icon: Sparkles },
    { href: "/security", label: "Security", icon: Shield },
    { href: "/optimization", label: "Optimization", icon: TrendingUp },
    { href: "/reports", label: "Reports", icon: FileText },
    { href: "/settings", label: "Settings", icon: Settings },
]

export function Sidebar() {
    const pathname = usePathname()
    
    return (
        <aside className="w-64 border-r border-[rgba(255,255,255,0.08)] bg-[rgba(15,15,20,0.95)] backdrop-blur-[20px] min-h-screen sticky top-0">
            <div className="p-6">
                {/* Finout 风格：简洁的 Logo */}
                <h1 className="text-xl font-bold tracking-tight text-foreground mb-8">CloudLens</h1>
                <nav className="space-y-1">
                    {navItems.map(item => {
                        const Icon = item.icon
                        const isActive = pathname === item.href || 
                                        (item.href !== "/" && pathname?.startsWith(item.href))
                        
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={`flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                                    isActive
                                        ? "bg-primary/15 text-primary border-l-2 border-l-primary"
                                        : "text-muted-foreground hover:text-foreground hover:bg-[rgba(255,255,255,0.05)]"
                                }`}
                            >
                                <Icon className={`h-4 w-4 ${isActive ? "text-primary" : ""}`} />
                                {item.label}
                            </Link>
                        )
                    })}
                </nav>
            </div>
        </aside>
    )
}






