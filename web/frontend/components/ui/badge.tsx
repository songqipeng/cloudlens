"use client"

import { ReactNode } from "react"

interface BadgeProps {
    children: ReactNode
    variant?: "default" | "success" | "warning" | "danger" | "info"
    size?: "sm" | "md" | "lg"
    className?: string
}

const variantClasses = {
    default: "bg-muted text-muted-foreground",
    success: "bg-green-500/10 text-green-500 border-green-500/20",
    warning: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
    danger: "bg-red-500/10 text-red-500 border-red-500/20",
    info: "bg-blue-500/10 text-blue-500 border-blue-500/20",
}

const sizeClasses = {
    sm: "text-xs px-2 py-0.5",
    md: "text-sm px-2.5 py-1",
    lg: "text-base px-3 py-1.5",
}

export function Badge({ 
    children, 
    variant = "default", 
    size = "md",
    className = ""
}: BadgeProps) {
    return (
        <span 
            className={`inline-flex items-center rounded-full border font-medium ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
        >
            {children}
        </span>
    )
}

interface StatusBadgeProps {
    status: string
    className?: string
}

export function StatusBadge({ status, className = "" }: StatusBadgeProps) {
    const statusMap: Record<string, { variant: BadgeProps["variant"], label: string }> = {
        "Running": { variant: "success", label: "运行中" },
        "Stopped": { variant: "warning", label: "已停止" },
        "Starting": { variant: "info", label: "启动中" },
        "Stopping": { variant: "warning", label: "停止中" },
        "Expired": { variant: "danger", label: "已过期" },
        "Pending": { variant: "info", label: "待处理" },
    }
    
    const config = statusMap[status] || { variant: "default" as const, label: status }
    
    return (
        <Badge variant={config.variant} className={className}>
            {config.label}
        </Badge>
    )
}









