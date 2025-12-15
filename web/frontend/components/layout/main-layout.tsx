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
            <main className="flex-1 p-8">
                {children}
            </main>
        </div>
    )
}





