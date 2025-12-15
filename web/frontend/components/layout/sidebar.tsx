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
    Settings 
} from "lucide-react"

const navItems = [
    { href: "/", label: "Dashboard", icon: LayoutDashboard },
    { href: "/resources", label: "Resources", icon: Server },
    { href: "/cost", label: "Cost", icon: DollarSign },
    { href: "/security", label: "Security", icon: Shield },
    { href: "/optimization", label: "Optimization", icon: TrendingUp },
    { href: "/reports", label: "Reports", icon: FileText },
    { href: "/settings", label: "Settings", icon: Settings },
]

export function Sidebar() {
    const pathname = usePathname()
    
    return (
        <aside className="w-64 border-r border-border bg-card/30 min-h-screen sticky top-0">
            <div className="p-6">
                <h1 className="text-xl font-bold tracking-tighter gradient-text mb-8">CloudLens</h1>
                <nav className="space-y-2">
                    {navItems.map(item => {
                        const Icon = item.icon
                        const isActive = pathname === item.href || 
                                        (item.href !== "/" && pathname?.startsWith(item.href))
                        
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={`flex items-center gap-3 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                                    isActive
                                        ? "bg-primary/10 text-primary"
                                        : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                                }`}
                            >
                                <Icon className="h-4 w-4" />
                                {item.label}
                            </Link>
                        )
                    })}
                </nav>
            </div>
        </aside>
    )
}





