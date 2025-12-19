"use client"

import { ReactNode } from "react"
import { Sidebar } from "./sidebar"

interface MainLayoutProps {
    children: ReactNode
}

export function MainLayout({ children }: MainLayoutProps) {
    return (
        <div className="min-h-screen bg-background text-foreground font-sans flex">
            <Sidebar />
            {/* Finout 风格：更大的内容区域，更好的间距 */}
            <main className="flex-1 p-6 md:p-8 lg:p-10 overflow-auto">
                {children}
            </main>
        </div>
    )
}







