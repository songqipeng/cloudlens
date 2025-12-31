"use client"

import { useEffect, useState } from "react"

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

export function RabbitLoading({ showText = true, delay = 0 }: { showText?: boolean, delay?: number }) {
    const [visible, setVisible] = useState(delay === 0)

    useEffect(() => {
        if (delay > 0) {
            const timer = setTimeout(() => setVisible(true), delay)
            return () => clearTimeout(timer)
        }
    }, [delay])

    if (!visible) return null

    return (
        <div className="flex flex-col items-center justify-center animate-fade-in">
            <div className="relative w-24 h-24 mb-2">
                {/* 运动线条 */}
                <div className="absolute top-1/2 -left-8 w-6 h-0.5 bg-primary/40 rounded-full animate-motion-line" style={{ top: '40%', animationDelay: '0s' }}></div>
                <div className="absolute top-1/2 -left-10 w-8 h-0.5 bg-primary/20 rounded-full animate-motion-line" style={{ top: '60%', animationDelay: '0.2s' }}></div>
                <div className="absolute top-1/2 -left-6 w-5 h-0.5 bg-primary/30 rounded-full animate-motion-line" style={{ top: '50%', animationDelay: '0.4s' }}></div>

                {/* 兔子主体 */}
                <div className="animate-rabbit-hop">
                    <svg viewBox="0 0 100 100" className="w-20 h-20 fill-primary drop-shadow-[0_0_8px_rgba(59,130,246,0.5)]">
                        {/* 尾巴 */}
                        <circle cx="15" cy="65" r="5" />
                        {/* 身体 */}
                        <path d="M20 60 Q20 40 50 40 Q80 40 85 60 L85 70 Q85 80 75 80 L25 80 Q15 80 15 70 Z" />
                        {/* 耳朵 */}
                        <g className="animate-rabbit-ear origin-bottom">
                            <path d="M55 40 Q50 10 60 10 Q70 10 65 40 Z" />
                            <path d="M65 40 Q60 15 70 15 Q80 15 75 40 Z" />
                        </g>
                        {/* 眼睛 */}
                        <circle cx="75" cy="55" r="2" fill="white" />
                        {/* 腿 */}
                        <rect x="30" y="75" width="10" height="8" rx="4" />
                        <rect x="60" y="75" width="10" height="8" rx="4" />
                    </svg>
                </div>

                {/* 阴影/灰尘 */}
                <div className="absolute bottom-1 left-4 right-4 h-2 bg-primary/10 rounded-full blur-[2px] animate-pulse"></div>
            </div>
            {showText && (
                <div className="text-center space-y-2 mt-4">
                    <p className="text-lg font-bold gradient-text tracking-wider">正在加载数据</p>
                    <div className="flex items-center justify-center gap-1.5">
                        <div className="w-1.5 h-1.5 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: '0s' }}></div>
                        <div className="w-1.5 h-1.5 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                        <div className="w-1.5 h-1.5 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                </div>
            )}
        </div>
    )
}

export function LoadingPage() {
    return (
        <div className="flex items-center justify-center min-h-[60vh]">
            <RabbitLoading delay={3000} />
        </div>
    )
}
