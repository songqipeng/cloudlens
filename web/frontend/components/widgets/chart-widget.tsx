"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ResponsiveContainer, AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from "recharts"
import { TreemapChart, HeatmapChart, SankeyChart } from "@/components/charts"
import { ChartExport } from "@/components/charts/chart-export"
import { useState } from "react"
import { ZoomIn, ZoomOut, Download } from "lucide-react"

interface ChartWidgetProps {
  title: string
  type: "line" | "area" | "bar" | "treemap" | "heatmap" | "sankey"
  data: any
  config?: {
    dataKey?: string
    xKey?: string
    yKey?: string
    colors?: string[]
    enableZoom?: boolean
    enableExport?: boolean
    [key: string]: any
  }
}

export function ChartWidget({
  title,
  type,
  data,
  config = {}
}: ChartWidgetProps) {
  const [zoomEnabled, setZoomEnabled] = useState(config.enableZoom !== false)
  const chartId = `chart-${title.replace(/\s+/g, "-")}-${Date.now()}`

  if (!data) {
    return (
      <Card className="h-full">
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-[300px] text-muted-foreground">
            暂无数据
          </div>
        </CardContent>
      </Card>
    )
  }

  const renderChart = () => {
    switch (type) {
      case "line":
      case "area":
        return (
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--muted))" />
            <XAxis
              dataKey={config.xKey || "date"}
              stroke="hsl(var(--muted-foreground))"
              fontSize={12}
            />
            <YAxis
              stroke="hsl(var(--muted-foreground))"
              fontSize={12}
              tickFormatter={(value) => {
                if (config.format === "currency") {
                  return value >= 10000 ? `¥${(value / 10000).toFixed(1)}万` : `¥${value}`
                }
                return value.toLocaleString()
              }}
            />
            <Tooltip
              formatter={(value: any) => [
                config.format === "currency" 
                  ? `¥${Number(value).toLocaleString()}` 
                  : Number(value).toLocaleString(),
                config.dataKey || "value"
              ]}
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "8px"
              }}
            />
            <Area
              type="monotone"
              dataKey={config.dataKey || "value"}
              stroke="hsl(var(--primary))"
              fill="hsl(var(--primary))"
              fillOpacity={0.2}
            />
          </AreaChart>
        )

      case "bar":
        return (
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--muted))" />
            <XAxis
              dataKey={config.xKey || "name"}
              stroke="hsl(var(--muted-foreground))"
              fontSize={12}
            />
            <YAxis
              stroke="hsl(var(--muted-foreground))"
              fontSize={12}
              tickFormatter={(value) => {
                if (config.format === "currency") {
                  return value >= 10000 ? `¥${(value / 10000).toFixed(1)}万` : `¥${value}`
                }
                return value.toLocaleString()
              }}
            />
            <Tooltip
              formatter={(value: any) => [
                config.format === "currency" 
                  ? `¥${Number(value).toLocaleString()}` 
                  : Number(value).toLocaleString(),
                config.dataKey || "value"
              ]}
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "8px"
              }}
            />
            <Bar dataKey={config.dataKey || "value"} fill="hsl(var(--primary))" />
          </BarChart>
        )

      case "treemap":
        return <TreemapChart data={data} colors={config.colors} />

      case "heatmap":
        return (
          <HeatmapChart
            data={data}
            xLabels={config.xLabels}
            yLabels={config.yLabels}
            colorScale={config.colorScale}
          />
        )

      case "sankey":
        return (
          <SankeyChart
            nodes={data.nodes || []}
            links={data.links || []}
            width={config.width}
            height={config.height}
          />
        )

      default:
        return (
          <div className="flex items-center justify-center h-[300px] text-muted-foreground">
            不支持的图表类型
          </div>
        )
    }
  }

  return (
    <Card className="h-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>{title}</CardTitle>
          <div className="flex items-center gap-2">
            {config.enableZoom !== false && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setZoomEnabled(!zoomEnabled)}
                title={zoomEnabled ? "禁用缩放" : "启用缩放"}
              >
                {zoomEnabled ? (
                  <ZoomOut className="h-4 w-4" />
                ) : (
                  <ZoomIn className="h-4 w-4" />
                )}
              </Button>
            )}
            {config.enableExport !== false && (
              <ChartExport chartId={chartId} title={title} />
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div id={chartId} className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            {renderChart()}
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}



