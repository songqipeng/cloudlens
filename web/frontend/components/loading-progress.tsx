"use client"

import { useEffect, useState } from "react"
import { Card, CardContent } from "@/components/ui/card"

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
          {/* 主加载动画 - 脉冲圆环 */}
          <div className="relative">
            {/* 外圈脉冲动画 */}
            <div className="absolute inset-0 rounded-full border-4 border-primary/20 animate-ping"></div>
            {/* 中圈旋转动画 */}
            <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-primary/40 animate-spin" style={{ animationDuration: "1.5s" }}></div>
            {/* 内圈旋转动画 */}
            <div className="relative w-20 h-20 rounded-full border-4 border-transparent border-t-primary border-r-primary/50 animate-spin" style={{ animationDuration: "1s" }}></div>
            {/* 中心点 */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-3 h-3 rounded-full bg-primary animate-pulse"></div>
            </div>
          </div>

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
            <div className="w-full max-w-md space-y-2">
              <div className="h-2 bg-muted/30 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-primary via-primary/80 to-primary rounded-full transition-all duration-300 ease-out relative"
                  style={{ width: `${Math.min(100, Math.max(0, progressPercent))}%` }}
                >
                  {/* 进度条光效 */}
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent" style={{ animation: "shimmer 2s infinite" }}></div>
                </div>
              </div>
              <div className="text-center text-xs text-muted-foreground">
                {Math.round(progressPercent)}%
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

