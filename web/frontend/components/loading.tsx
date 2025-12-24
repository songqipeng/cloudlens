"use client"

export function LoadingSpinner({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
    const sizeClasses = {
        sm: "h-4 w-4",
        md: "h-8 w-8",
        lg: "h-12 w-12",
    }
    
    return (
        <div className={`${sizeClasses[size]} border-4 border-primary/20 border-t-primary rounded-full animate-spin`} />
    )
}

export function LoadingSkeleton({ className = "" }: { className?: string }) {
    return (
        <div className={`animate-pulse bg-muted rounded ${className}`} />
    )
}

export function LoadingPage() {
    return (
        <div className="flex items-center justify-center min-h-screen">
            <div className="text-center space-y-4">
                <LoadingSpinner size="lg" />
                <p className="text-muted-foreground">加载中...</p>
            </div>
        </div>
    )
}











