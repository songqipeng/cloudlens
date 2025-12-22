import { cn } from "@/lib/utils"

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "text" | "circular" | "rectangular"
  width?: string | number
  height?: string | number
}

export function Skeleton({ 
  className, 
  variant = "default",
  width,
  height,
  ...props 
}: SkeletonProps) {
  const baseClasses = "animate-pulse bg-muted/50 rounded"
  
  const variantClasses = {
    default: "rounded-lg",
    text: "rounded h-4",
    circular: "rounded-full",
    rectangular: "rounded-none",
  }
  
  const style: React.CSSProperties = {}
  if (width) style.width = typeof width === 'number' ? `${width}px` : width
  if (height) style.height = typeof height === 'number' ? `${height}px` : height
  
  return (
    <div
      className={cn(baseClasses, variantClasses[variant], className)}
      style={style}
      {...props}
    />
  )
}

// 预定义的Skeleton组件
export function SkeletonCard() {
  return (
    <div className="rounded-lg border border-border/50 bg-card/50 p-6 space-y-4">
      <Skeleton variant="text" width="60%" height={20} />
      <Skeleton variant="text" width="40%" height={32} />
      <Skeleton variant="text" width="80%" height={14} />
    </div>
  )
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {/* 表头 */}
      <div className="flex gap-4 pb-3 border-b border-border/50">
        <Skeleton variant="text" width="25%" height={16} />
        <Skeleton variant="text" width="25%" height={16} />
        <Skeleton variant="text" width="25%" height={16} />
        <Skeleton variant="text" width="25%" height={16} />
      </div>
      {/* 表格行 */}
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4">
          <Skeleton variant="text" width="25%" height={20} />
          <Skeleton variant="text" width="25%" height={20} />
          <Skeleton variant="text" width="25%" height={20} />
          <Skeleton variant="text" width="25%" height={20} />
        </div>
      ))}
    </div>
  )
}




