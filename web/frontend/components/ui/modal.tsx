"use client"

import { ReactNode, useEffect } from "react"
import { X } from "lucide-react"

interface ModalProps {
    isOpen: boolean
    onClose: () => void
    title?: string
    children: ReactNode
    size?: "sm" | "md" | "lg" | "xl"
    showCloseButton?: boolean
}

const sizeClasses = {
    sm: "max-w-md",
    md: "max-w-lg",
    lg: "max-w-2xl",
    xl: "max-w-4xl",
}

export function Modal({ 
    isOpen, 
    onClose, 
    title, 
    children, 
    size = "md",
    showCloseButton = true 
}: ModalProps) {
    useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = "hidden"
        } else {
            document.body.style.overflow = "unset"
        }
        return () => {
            document.body.style.overflow = "unset"
        }
    }, [isOpen])
    
    if (!isOpen) return null
    
    return (
        <div 
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
            onClick={onClose}
        >
            <div 
                className={`bg-background border border-border rounded-lg shadow-lg ${sizeClasses[size]} w-full m-4 max-h-[90vh] overflow-y-auto`}
                onClick={(e) => e.stopPropagation()}
            >
                {title && (
                    <div className="flex items-center justify-between p-6 border-b">
                        <h2 className="text-xl font-semibold">{title}</h2>
                        {showCloseButton && (
                            <button
                                onClick={onClose}
                                className="p-1 rounded-md hover:bg-muted transition-colors"
                            >
                                <X className="h-5 w-5" />
                            </button>
                        )}
                    </div>
                )}
                <div className="p-6">
                    {children}
                </div>
            </div>
        </div>
    )
}

interface ConfirmModalProps {
    isOpen: boolean
    onClose: () => void
    onConfirm: () => void
    title: string
    message: string
    confirmText?: string
    cancelText?: string
    variant?: "default" | "danger"
}

export function ConfirmModal({
    isOpen,
    onClose,
    onConfirm,
    title,
    message,
    confirmText = "确认",
    cancelText = "取消",
    variant = "default"
}: ConfirmModalProps) {
    const handleConfirm = () => {
        onConfirm()
        onClose()
    }
    
    return (
        <Modal isOpen={isOpen} onClose={onClose} title={title} size="sm">
            <div className="space-y-4">
                <p className="text-muted-foreground">{message}</p>
                <div className="flex justify-end gap-3">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 rounded-md border border-border hover:bg-muted transition-colors"
                    >
                        {cancelText}
                    </button>
                    <button
                        onClick={handleConfirm}
                        className={`px-4 py-2 rounded-md text-white transition-colors ${
                            variant === "danger" 
                                ? "bg-destructive hover:bg-destructive/90" 
                                : "bg-primary hover:bg-primary/90"
                        }`}
                    >
                        {confirmText}
                    </button>
                </div>
            </div>
        </Modal>
    )
}





