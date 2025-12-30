"use client"

import { ResponsiveContainer, Treemap, Tooltip, Cell } from "recharts"

interface TreemapChartProps {
  data: Array<{ name: string; value: number; [key: string]: any }>
  dataKey?: string
  nameKey?: string
  colors?: string[]
}

const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#f97316"]

export function TreemapChart({
  data,
  dataKey = "value",
  nameKey = "name",
  colors = COLORS
}: TreemapChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-full min-h-[200px] text-muted-foreground">
        暂无数据
      </div>
    )
  }

  return (
    <Treemap
      data={data}
      dataKey={dataKey}
      nameKey={nameKey}
      stroke="#fff"
      fill="#8884d8"
    >
      <Tooltip
        formatter={(value: any, name: string) => [
          typeof value === "number" ? value.toLocaleString() : value,
          name
        ]}
        contentStyle={{
          backgroundColor: "hsl(var(--card))",
          border: "1px solid hsl(var(--border))",
          borderRadius: "8px"
        }}
      />
      {data.map((entry, index) => (
        <Cell
          key={`cell-${index}`}
          fill={colors[index % colors.length]}
        />
      ))}
    </Treemap>
  )
}






