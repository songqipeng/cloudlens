"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { TrendingUp, TrendingDown, Minus } from "lucide-react"

interface MetricWidgetProps {
  title: string
  value: number
  format?: "currency" | "percentage" | "number"
  trend?: {
    value: number
    percentage: number
    direction: "up" | "down" | "neutral"
  }
  subtitle?: string
  icon?: React.ReactNode
}

export function MetricWidget({
  title,
  value,
  format = "number",
  trend,
  subtitle,
  icon
}: MetricWidgetProps) {
  const formatValue = (val: number) => {
    switch (format) {
      case "currency":
        return `¥${val.toLocaleString()}`
      case "percentage":
        return `${val.toFixed(1)}%`
      default:
        return val.toLocaleString()
    }
  }

  const getTrendColor = () => {
    if (!trend) return "text-muted-foreground"
    switch (trend.direction) {
      case "up":
        return "text-red-500"
      case "down":
        return "text-green-500"
      default:
        return "text-muted-foreground"
    }
  }

  const TrendIcon = trend?.direction === "up" 
    ? TrendingUp 
    : trend?.direction === "down" 
    ? TrendingDown 
    : Minus

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            {title}
          </CardTitle>
          {icon && <div className="text-muted-foreground">{icon}</div>}
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <div className="text-3xl font-bold">{formatValue(value)}</div>
          {subtitle && (
            <div className="text-sm text-muted-foreground">{subtitle}</div>
          )}
          {trend && (
            <div className={`flex items-center gap-1 text-sm ${getTrendColor()}`}>
              <TrendIcon className="h-4 w-4" />
              <span>
                {trend.percentage > 0 ? "+" : ""}
                {trend.percentage.toFixed(1)}%
              </span>
              <span className="text-muted-foreground">
                ({formatValue(trend.value)})
              </span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}




