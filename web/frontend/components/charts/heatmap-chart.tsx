"use client"

import { ResponsiveContainer, Cell } from "recharts"

interface HeatmapChartProps {
  data: Array<{
    x: string | number
    y: string | number
    value: number
    [key: string]: any
  }>
  xLabels?: string[]
  yLabels?: string[]
  colorScale?: (value: number) => string
}

// 默认颜色比例尺
function defaultColorScale(value: number, max: number): string {
  const ratio = value / max
  if (ratio < 0.2) return "#e0f2fe" // 浅蓝
  if (ratio < 0.4) return "#7dd3fc" // 中蓝
  if (ratio < 0.6) return "#0ea5e9" // 蓝
  if (ratio < 0.8) return "#0284c7" // 深蓝
  return "#0369a1" // 最深蓝
}

export function HeatmapChart({
  data,
  xLabels = [],
  yLabels = [],
  colorScale
}: HeatmapChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-full min-h-[200px] text-muted-foreground">
        暂无数据
      </div>
    )
  }

  // 计算最大值用于颜色比例
  const maxValue = Math.max(...data.map(d => d.value))
  const getColor = colorScale || ((v: number) => defaultColorScale(v, maxValue))

  // 构建网格数据
  const gridData: Record<string, Record<string, number>> = {}
  data.forEach(item => {
    if (!gridData[String(item.y)]) {
      gridData[String(item.y)] = {}
    }
    gridData[String(item.y)][String(item.x)] = item.value
  })

  const uniqueX = xLabels.length > 0 ? xLabels : [...new Set(data.map(d => String(d.x)))]
  const uniqueY = yLabels.length > 0 ? yLabels : [...new Set(data.map(d => String(d.y)))]

  return (
    <div className="w-full h-full p-4">
      <div className="grid gap-1" style={{ gridTemplateColumns: `repeat(${uniqueX.length}, 1fr)` }}>
        {/* Y轴标签 */}
        <div className="col-span-1 row-span-1"></div>
        {uniqueX.map((x, idx) => (
          <div
            key={x}
            className="text-xs text-muted-foreground text-center font-medium"
            style={{ gridColumn: idx + 2 }}
          >
            {x}
          </div>
        ))}
        
        {/* 数据行 */}
        {uniqueY.map((y, rowIdx) => (
          <>
            <div
              key={`y-${y}`}
              className="text-xs text-muted-foreground font-medium flex items-center"
              style={{ gridRow: rowIdx + 2 }}
            >
              {y}
            </div>
            {uniqueX.map((x, colIdx) => {
              const value = gridData[y]?.[x] || 0
              return (
                <div
                  key={`${y}-${x}`}
                  className="aspect-square rounded border border-border/50 flex items-center justify-center text-xs font-medium transition-all hover:scale-110"
                  style={{
                    backgroundColor: getColor(value),
                    gridColumn: colIdx + 2,
                    gridRow: rowIdx + 2
                  }}
                  title={`${x} × ${y}: ${value.toLocaleString()}`}
                >
                  {value > 0 && (
                    <span className={value > maxValue * 0.5 ? "text-white" : "text-foreground"}>
                      {value > 1000 ? `${(value / 1000).toFixed(1)}k` : value}
                    </span>
                  )}
                </div>
              )
            })}
          </>
        ))}
      </div>
    </div>
  )
}



