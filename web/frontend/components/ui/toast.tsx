"use client"

import { useEffect, useState } from "react"
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from "lucide-react"

export type ToastType = "success" | "error" | "info" | "warning"

export interface Toast {
  id: string
  message: string
  type: ToastType
  duration?: number
}

interface ToastProps {
  toast: Toast
  onClose: (id: string) => void
}

function ToastItem({ toast, onClose }: ToastProps) {
  useEffect(() => {
    if (toast.duration !== 0) {
      const timer = setTimeout(() => {
        onClose(toast.id)
      }, toast.duration || 3000)
      return () => clearTimeout(timer)
    }
  }, [toast.id, toast.duration, onClose])

  const icons = {
    success: <CheckCircle className="h-5 w-5 text-green-500" />,
    error: <AlertCircle className="h-5 w-5 text-red-500" />,
    warning: <AlertTriangle className="h-5 w-5 text-yellow-500" />,
    info: <Info className="h-5 w-5 text-blue-500" />
  }

  const bgColors = {
    success: "bg-[rgba(34,197,94,0.15)] border-green-500/30 dark:bg-[rgba(34,197,94,0.1)]",
    error: "bg-[rgba(239,68,68,0.15)] border-red-500/30 dark:bg-[rgba(239,68,68,0.1)]",
    warning: "bg-[rgba(234,179,8,0.15)] border-yellow-500/30 dark:bg-[rgba(234,179,8,0.1)]",
    info: "bg-[rgba(59,130,246,0.15)] border-blue-500/30 dark:bg-[rgba(59,130,246,0.1)]"
  }

  return (
    <div
      className={`
        flex items-start gap-3 p-4 rounded-lg border backdrop-blur-md
        ${bgColors[toast.type]}
        shadow-lg shadow-black/20 min-w-[320px] max-w-[500px]
        bg-background/95 dark:bg-background/90
      `}
      style={{
        animation: "slideIn 0.3s ease-out"
      }}
    >
      <div className="flex-shrink-0 mt-0.5">
        {icons[toast.type]}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-foreground break-words">
          {toast.message}
        </p>
      </div>
      <button
        onClick={() => onClose(toast.id)}
        className="flex-shrink-0 text-muted-foreground hover:text-foreground transition-colors"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  )
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<Toast[]>([])

  useEffect(() => {
    // 监听全局 toast 事件
    const handleToast = (event: CustomEvent<Omit<Toast, "id">>) => {
      const toast: Toast = {
        ...event.detail,
        id: Math.random().toString(36).substring(2, 9)
      }
      setToasts((prev) => [...prev, toast])
    }

    window.addEventListener("toast" as any, handleToast as EventListener)
    return () => {
      window.removeEventListener("toast" as any, handleToast as EventListener)
    }
  }, [])

  const handleClose = (id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id))
  }

  if (toasts.length === 0) return null

  return (
    <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none">
      {toasts.map((toast) => (
        <div key={toast.id} className="pointer-events-auto">
          <ToastItem toast={toast} onClose={handleClose} />
        </div>
      ))}
    </div>
  )
}

// 便捷函数
export function toast(message: string, type: ToastType = "info", duration: number = 3000) {
  const event = new CustomEvent("toast", {
    detail: { message, type, duration }
  })
  window.dispatchEvent(event)
}

export function toastSuccess(message: string, duration?: number) {
  toast(message, "success", duration)
}

export function toastError(message: string, duration?: number) {
  toast(message, "error", duration || 5000)
}

export function toastWarning(message: string, duration?: number) {
  toast(message, "warning", duration)
}

export function toastInfo(message: string, duration?: number) {
  toast(message, "info", duration)
}

