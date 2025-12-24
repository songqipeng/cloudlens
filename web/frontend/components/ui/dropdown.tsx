"use client"

import { useState, useRef, useEffect, ReactNode } from "react"
import { ChevronDown } from "lucide-react"

interface DropdownOption {
    label: string
    value: string
    icon?: ReactNode
    disabled?: boolean
}

interface DropdownProps {
    options: DropdownOption[]
    value?: string
    onChange?: (value: string) => void
    placeholder?: string
    className?: string
}

export function Dropdown({ 
    options, 
    value, 
    onChange, 
    placeholder = "选择...",
    className = ""
}: DropdownProps) {
    const [isOpen, setIsOpen] = useState(false)
    const dropdownRef = useRef<HTMLDivElement>(null)
    
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false)
            }
        }
        
        document.addEventListener("mousedown", handleClickOutside)
        return () => document.removeEventListener("mousedown", handleClickOutside)
    }, [])
    
    const selectedOption = options.find(opt => opt.value === value)
    
    return (
        <div className={`relative ${className}`} ref={dropdownRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full flex items-center justify-between px-3 py-2 rounded-md border border-input bg-background hover:bg-muted transition-colors"
            >
                <span className="text-sm">
                    {selectedOption ? (
                        <span className="flex items-center gap-2">
                            {selectedOption.icon}
                            {selectedOption.label}
                        </span>
                    ) : (
                        <span className="text-muted-foreground">{placeholder}</span>
                    )}
                </span>
                <ChevronDown className={`h-4 w-4 transition-transform ${isOpen ? "rotate-180" : ""}`} />
            </button>
            
            {isOpen && (
                <div className="absolute z-50 w-full mt-1 bg-background border border-border rounded-md shadow-lg max-h-60 overflow-y-auto">
                    {options.map(option => (
                        <button
                            key={option.value}
                            onClick={() => {
                                if (!option.disabled) {
                                    onChange?.(option.value)
                                    setIsOpen(false)
                                }
                            }}
                            disabled={option.disabled}
                            className={`w-full text-left px-3 py-2 text-sm hover:bg-muted transition-colors flex items-center gap-2 ${
                                option.value === value ? "bg-primary/10 text-primary" : ""
                            } ${option.disabled ? "opacity-50 cursor-not-allowed" : ""}`}
                        >
                            {option.icon}
                            {option.label}
                        </button>
                    ))}
                </div>
            )}
        </div>
    )
}

interface DropdownMenuProps {
    trigger: ReactNode
    items: Array<{
        label: string
        onClick: () => void
        icon?: ReactNode
        disabled?: boolean
        variant?: "default" | "danger"
    }>
    align?: "left" | "right"
}

export function DropdownMenu({ trigger, items, align = "right" }: DropdownMenuProps) {
    const [isOpen, setIsOpen] = useState(false)
    const menuRef = useRef<HTMLDivElement>(null)
    
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
                setIsOpen(false)
            }
        }
        
        document.addEventListener("mousedown", handleClickOutside)
        return () => document.removeEventListener("mousedown", handleClickOutside)
    }, [])
    
    return (
        <div className="relative" ref={menuRef}>
            <div onClick={() => setIsOpen(!isOpen)}>
                {trigger}
            </div>
            
            {isOpen && (
                <div className={`absolute z-50 mt-1 min-w-[160px] bg-background border border-border rounded-md shadow-lg ${
                    align === "right" ? "right-0" : "left-0"
                }`}>
                    {items.map((item, idx) => (
                        <button
                            key={idx}
                            onClick={() => {
                                if (!item.disabled) {
                                    item.onClick()
                                    setIsOpen(false)
                                }
                            }}
                            disabled={item.disabled}
                            className={`w-full text-left px-3 py-2 text-sm hover:bg-muted transition-colors flex items-center gap-2 ${
                                item.variant === "danger" ? "text-destructive" : ""
                            } ${item.disabled ? "opacity-50 cursor-not-allowed" : ""}`}
                        >
                            {item.icon}
                            <span className={item.variant === "danger" ? "" : ""}>{item.label}</span>
                        </button>
                    ))}
                </div>
            )}
        </div>
    )
}











