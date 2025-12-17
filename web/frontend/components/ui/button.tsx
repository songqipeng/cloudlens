import * as React from "react"
import { cn } from "@/lib/utils"

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link"
  size?: "default" | "sm" | "lg" | "icon"
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => {
    return (
      <button
        className={cn(
          // Finout 风格：圆角8px，明确的状态反馈，微动画
          "inline-flex items-center justify-center rounded-lg text-sm font-medium transition-all duration-200",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background",
          "disabled:pointer-events-none disabled:opacity-50",
          {
            // 主按钮：蓝色背景，hover时加深，轻微阴影
            "bg-primary text-primary-foreground hover:bg-primary/90 active:bg-primary/95": variant === "default",
            "shadow-[0_2px_8px_rgba(59,130,246,0.2)] hover:shadow-[0_4px_12px_rgba(59,130,246,0.3)]": variant === "default",
            "hover:-translate-y-0.5 active:translate-y-0": variant === "default",
            
            // 危险按钮
            "bg-destructive text-destructive-foreground hover:bg-destructive/90 active:bg-destructive/95": variant === "destructive",
            "shadow-[0_2px_8px_rgba(239,68,68,0.2)] hover:shadow-[0_4px_12px_rgba(239,68,68,0.3)]": variant === "destructive",
            
            // 轮廓按钮
            "border border-[rgba(255,255,255,0.1)] bg-transparent hover:bg-accent hover:text-accent-foreground hover:border-primary/50": variant === "outline",
            
            // 次要按钮
            "bg-secondary text-secondary-foreground hover:bg-secondary/80": variant === "secondary",
            
            // 幽灵按钮
            "hover:bg-accent hover:text-accent-foreground": variant === "ghost",
            
            // 链接按钮
            "text-primary underline-offset-4 hover:underline": variant === "link",
          },
          {
            "h-10 px-4 py-2 rounded-lg": size === "default",
            "h-9 rounded-md px-3": size === "sm",
            "h-11 rounded-lg px-8": size === "lg",
            "h-10 w-10 rounded-lg": size === "icon",
          },
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button }

