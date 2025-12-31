"use client"

import { useEffect, useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { RabbitLoading } from "@/components/loading"

interface LoadingProgressProps {
  message?: string
  subMessage?: string
  showProgress?: boolean
  progressPercent?: number
  estimatedTime?: number // 预估剩余时间（秒）
}

/**
 * 漂亮的加载进度组件
 * 适用于长时间加载的场景（>5秒）
 */
export function LoadingProgress({
  message = "正在加载数据...",
  subMessage,
  showProgress = false,
  progressPercent = 0,
  estimatedTime
}: LoadingProgressProps) {
  const [dots, setDots] = useState("")

  // 动态显示加载点
  useEffect(() => {
    const interval = setInterval(() => {
      setDots((prev) => {
        if (prev.length >= 3) return ""
        return prev + "."
      })
    }, 500)
    return () => clearInterval(interval)
  }, [])

  const formatTime = (seconds: number) => {
    if (seconds < 60) return `${Math.ceil(seconds)}秒`
    const mins = Math.floor(seconds / 60)
    const secs = Math.ceil(seconds % 60)
    return `${mins}分${secs}秒`
  }

  return (
    <Card className="glass border border-border/50">
      <CardContent className="py-16">
        <div className="flex flex-col items-center justify-center space-y-6">
          {/* 主加载动画 - 活泼的小兔子 */}
          <RabbitLoading showText={false} delay={3000} />

          {/* 文字提示 */}
          <div className="text-center space-y-2">
            <p className="text-lg font-medium text-foreground">
              {message}{dots}
            </p>
            {subMessage && (
              <p className="text-sm text-muted-foreground">
                {subMessage}
              </p>
            )}
            {estimatedTime && estimatedTime > 0 && (
              <p className="text-xs text-muted-foreground mt-2">
                预计还需 {formatTime(estimatedTime)}
              </p>
            )}
          </div>

          {/* 进度条（可选） */}
          {showProgress && (
            <div className="w-full max-w-2xl space-y-3 animate-fade-in">
              <div className="h-4 bg-muted/30 rounded-full overflow-hidden shadow-inner relative border border-border/20">
                {/* 背景动画 - 脉冲效果 */}
                <div className="absolute inset-0 bg-gradient-to-r from-primary/5 via-primary/15 to-primary/5 animate-pulse"></div>

                {/* 进度条主体 */}
                <div
                  className="h-full bg-gradient-to-r from-primary via-blue-500 to-primary rounded-full transition-all duration-500 ease-out relative overflow-hidden"
                  style={{ width: `${Math.min(100, Math.max(0, progressPercent))}%` }}
                >
                  {/* 进度条光效动画 - 从左到右扫过（增强版） */}
                  <div
                    className="absolute inset-0 bg-gradient-to-r from-transparent via-white/60 to-transparent"
                    style={{
                      width: "40%",
                      transform: "skewX(-20deg) translateX(-200%)",
                      animation: "shimmer 2s infinite",
                    }}
                  ></div>

                  {/* 进度条内部高光 - 顶部渐变 */}
                  <div className="absolute top-0 left-0 right-0 h-1/2 bg-gradient-to-b from-white/50 via-white/30 to-transparent rounded-t-full"></div>

                  {/* 进度条边缘光效 - 右侧发光 */}
                  <div className="absolute right-0 top-0 bottom-0 w-3 bg-gradient-to-l from-primary via-blue-400 to-transparent opacity-70 blur-sm"></div>

                  {/* 进度条内部粒子效果 */}
                  <div className="absolute inset-0">
                    {[0, 1, 2].map((i) => (
                      <div
                        key={i}
                        className="absolute top-1/2 w-1 h-1 rounded-full bg-white/80 animate-pulse"
                        style={{
                          left: `${20 + i * 30}%`,
                          animationDelay: `${i * 0.3}s`,
                          animationDuration: "1.5s",
                          transform: "translateY(-50%)",
                        }}
                      />
                    ))}
                  </div>
                </div>

                {/* 进度条边缘发光效果 */}
                <div
                  className="absolute top-0 bottom-0 bg-primary/30 blur-md transition-all duration-500"
                  style={{
                    width: `${Math.min(100, Math.max(0, progressPercent))}%`,
                    right: 0,
                  }}
                ></div>
              </div>

              {/* 进度百分比显示 */}
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground font-medium">
                  {subMessage || "处理中..."}
                </span>
                <span className="text-primary font-bold tabular-nums transition-all duration-300">
                  {Math.round(progressPercent)}%
                </span>
              </div>
            </div>
          )}

          {/* 装饰性粒子效果 */}
          <div className="flex gap-2">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="w-2 h-2 rounded-full bg-primary/40 animate-pulse"
                style={{
                  animationDelay: `${i * 0.2}s`,
                  animationDuration: "1.5s"
                }}
              />
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * 智能加载组件 - 自动在超过5秒时显示进度动画
 */
export function SmartLoadingProgress({
  message,
  subMessage,
  loading,
  startTime,
  estimatedDuration
}: {
  message?: string
  subMessage?: string
  loading: boolean
  startTime?: number
  estimatedDuration?: number // 预估总时长（秒）
}) {
  const [showProgress, setShowProgress] = useState(false)
  const [progressPercent, setProgressPercent] = useState(0)
  const [estimatedTime, setEstimatedTime] = useState<number>()

  useEffect(() => {
    if (!loading || !startTime) {
      setShowProgress(false)
      setProgressPercent(0)
      setEstimatedTime(undefined)
      return
    }

    // 5秒后显示进度动画
    const progressTimer = setTimeout(() => {
      setShowProgress(true)
    }, 5000)

    // 更新进度
    const progressInterval = setInterval(() => {
      const elapsed = (Date.now() - startTime) / 1000

      if (estimatedDuration) {
        const percent = Math.min(95, (elapsed / estimatedDuration) * 100)
        setProgressPercent(percent)
        const remaining = Math.max(0, estimatedDuration - elapsed)
        setEstimatedTime(remaining)
      } else {
        // 没有预估时间时，使用模拟进度（前快后慢）
        const percent = Math.min(90, 20 + (elapsed / 10) * 70)
        setProgressPercent(percent)
      }
    }, 500)

    return () => {
      clearTimeout(progressTimer)
      clearInterval(progressInterval)
    }
  }, [loading, startTime, estimatedDuration])

  if (!loading) return null

  return (
    <LoadingProgress
      message={message}
      subMessage={subMessage}
      showProgress={showProgress}
      progressPercent={progressPercent}
      estimatedTime={estimatedTime}
    />
  )
}

