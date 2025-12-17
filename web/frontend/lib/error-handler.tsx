"use client"

import { ReactNode } from "react"

interface ErrorBoundaryProps {
    children: ReactNode
    fallback?: ReactNode
}

interface ErrorDisplayProps {
    error: Error
    onRetry?: () => void
}

export function ErrorDisplay({ error, onRetry }: ErrorDisplayProps) {
    return (
        <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
            <div className="text-red-500 text-lg font-medium">错误</div>
            <div className="text-muted-foreground text-sm">{error.message}</div>
            {onRetry && (
                <button
                    onClick={onRetry}
                    className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
                >
                    重试
                </button>
            )}
        </div>
    )
}

export function handleApiError(error: any): string {
    if (error instanceof Error) {
        return error.message
    }
    if (typeof error === "string") {
        return error
    }
    return "未知错误"
}






