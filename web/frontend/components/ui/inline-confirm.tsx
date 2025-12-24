"use client"

import { useEffect, useState } from "react"
import { CheckCircle2, XCircle, X } from "lucide-react"

interface InlineConfirmProps {
  message: string
  onConfirm: () => void
  onCancel: () => void
  confirmText?: string
  cancelText?: string
  variant?: "default" | "danger"
  position?: "top" | "bottom" | "inline"
}

/**
 * 页面内确认提示组件
 * 显示在页面内，而不是弹窗
 */
export function InlineConfirm({
  message,
  onConfirm,
  onCancel,
  confirmText = "确认",
  cancelText = "取消",
  variant = "default",
  position = "top"
}: InlineConfirmProps) {
  const [isVisible, setIsVisible] = useState(true)

  useEffect(() => {
    // 自动消失（可选）
    // const timer = setTimeout(() => {
    //   setIsVisible(false)
    //   onCancel()
    // }, 10000)
    // return () => clearTimeout(timer)
  }, [])

  if (!isVisible) return null

  const handleConfirm = () => {
    setIsVisible(false)
    onConfirm()
  }

  const handleCancel = () => {
    setIsVisible(false)
    onCancel()
  }

  const positionClasses = {
    top: "top-4 left-1/2 -translate-x-1/2",
    bottom: "bottom-4 left-1/2 -translate-x-1/2",
    inline: "relative"
  }

  return (
    <div
      className={`fixed z-50 ${positionClasses[position]} animate-in slide-in-from-top-2 duration-200`}
      style={position === "inline" ? { position: "relative" } : {}}
    >
      <div className="bg-background border border-border rounded-lg shadow-lg p-4 min-w-[320px] max-w-md">
        <div className="flex items-start gap-3">
          <div className={`flex-shrink-0 mt-0.5 ${
            variant === "danger" ? "text-destructive" : "text-primary"
          }`}>
            {variant === "danger" ? (
              <XCircle className="h-5 w-5" />
            ) : (
              <CheckCircle2 className="h-5 w-5" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-foreground mb-3">
              {message}
            </p>
            <div className="flex items-center gap-2 justify-end">
              <button
                onClick={handleCancel}
                className="px-3 py-1.5 text-sm rounded-md border border-border hover:bg-muted transition-colors"
              >
                {cancelText}
              </button>
              <button
                onClick={handleConfirm}
                className={`px-3 py-1.5 text-sm rounded-md text-white transition-colors ${
                  variant === "danger"
                    ? "bg-destructive hover:bg-destructive/90"
                    : "bg-primary hover:bg-primary/90"
                }`}
              >
                {confirmText}
              </button>
            </div>
          </div>
          <button
            onClick={handleCancel}
            className="flex-shrink-0 p-1 rounded-md hover:bg-muted transition-colors"
          >
            <X className="h-4 w-4 text-muted-foreground" />
          </button>
        </div>
      </div>
    </div>
  )
}

/**
 * Hook 用于管理页面内确认提示
 */
export function useInlineConfirm() {
  const [confirmState, setConfirmState] = useState<{
    message: string
    onConfirm: () => void
    variant?: "default" | "danger"
    confirmText?: string
    cancelText?: string
  } | null>(null)

  const showConfirm = (
    message: string,
    onConfirm: () => void,
    options?: {
      variant?: "default" | "danger"
      confirmText?: string
      cancelText?: string
    }
  ) => {
    setConfirmState({
      message,
      onConfirm,
      variant: options?.variant || "default",
      confirmText: options?.confirmText,
      cancelText: options?.cancelText
    })
  }

  const hideConfirm = () => {
    setConfirmState(null)
  }

  const ConfirmComponent = confirmState ? (
    <InlineConfirm
      message={confirmState.message}
      onConfirm={() => {
        confirmState.onConfirm()
        hideConfirm()
      }}
      onCancel={hideConfirm}
      variant={confirmState.variant}
      confirmText={confirmState.confirmText}
      cancelText={confirmState.cancelText}
    />
  ) : null

  return {
    showConfirm,
    hideConfirm,
    ConfirmComponent
  }
}

