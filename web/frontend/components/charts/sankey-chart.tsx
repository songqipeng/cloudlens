"use client"

import { ResponsiveContainer } from "recharts"

interface SankeyNode {
  name: string
}

interface SankeyLink {
  source: number
  target: number
  value: number
}

interface SankeyChartProps {
  nodes: SankeyNode[]
  links: SankeyLink[]
  width?: number
  height?: number
}

// 简化的Sankey图实现（使用SVG）
export function SankeyChart({
  nodes,
  links,
  width = 800,
  height = 400
}: SankeyChartProps) {
  if (!nodes || !links || nodes.length === 0 || links.length === 0) {
    return (
      <div className="flex items-center justify-center h-full min-h-[200px] text-muted-foreground">
        暂无数据
      </div>
    )
  }

  // 计算节点位置（简化版：垂直布局）
  const nodeHeight = height / nodes.length
  const nodeWidth = 100
  const nodePositions = nodes.map((_, index) => ({
    x: index % 2 === 0 ? 50 : width - nodeWidth - 50,
    y: (index * nodeHeight) + (nodeHeight / 2) - 15
  }))

  return (
    <ResponsiveContainer width="100%" height="100%">
      <svg width={width} height={height} className="overflow-visible">
        {/* 绘制连接线 */}
        {links.map((link, index) => {
          const source = nodePositions[link.source]
          const target = nodePositions[link.target]
          if (!source || !target) return null

          const midX = (source.x + target.x) / 2
          const path = `M ${source.x + nodeWidth} ${source.y} 
                       C ${midX} ${source.y}, ${midX} ${target.y}, ${target.x} ${target.y}`

          return (
            <path
              key={index}
              d={path}
              stroke="hsl(var(--primary))"
              strokeWidth={Math.max(2, Math.min(link.value / 10, 20))}
              fill="none"
              opacity={0.6}
            />
          )
        })}

        {/* 绘制节点 */}
        {nodes.map((node, index) => {
          const pos = nodePositions[index]
          if (!pos) return null

          return (
            <g key={index}>
              <rect
                x={pos.x}
                y={pos.y}
                width={nodeWidth}
                height={30}
                fill="hsl(var(--primary))"
                rx={4}
                className="hover:opacity-80 transition-opacity"
              />
              <text
                x={pos.x + nodeWidth / 2}
                y={pos.y + 20}
                textAnchor="middle"
                fill="white"
                fontSize={12}
                fontWeight="medium"
              >
                {node.name}
              </text>
            </g>
          )
        })}
      </svg>
    </ResponsiveContainer>
  )
}




