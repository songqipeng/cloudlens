"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useState } from "react"
import { ChevronUp, ChevronDown } from "lucide-react"

interface TableWidgetProps {
  title: string
  data: Array<Record<string, any>>
  columns?: Array<{
    key: string
    label: string
    sortable?: boolean
    formatter?: (value: any) => string
  }>
  pageSize?: number
  showPagination?: boolean
}

export function TableWidget({
  title,
  data,
  columns,
  pageSize = 10,
  showPagination = true
}: TableWidgetProps) {
  const [currentPage, setCurrentPage] = useState(1)
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc")

  if (!data || data.length === 0) {
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

  // 自动生成列（如果没有提供）
  const tableColumns = columns || Object.keys(data[0] || {}).map(key => ({
    key,
    label: key,
    sortable: true
  }))

  // 排序
  const sortedData = [...data].sort((a, b) => {
    if (!sortKey) return 0
    
    const aVal = a[sortKey]
    const bVal = b[sortKey]
    
    if (aVal === bVal) return 0
    
    const comparison = aVal > bVal ? 1 : -1
    return sortOrder === "asc" ? comparison : -comparison
  })

  // 分页
  const totalPages = Math.ceil(sortedData.length / pageSize)
  const paginatedData = showPagination
    ? sortedData.slice((currentPage - 1) * pageSize, currentPage * pageSize)
    : sortedData

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc")
    } else {
      setSortKey(key)
      setSortOrder("asc")
    }
  }

  const formatValue = (value: any, formatter?: (v: any) => string) => {
    if (formatter) return formatter(value)
    if (typeof value === "number") return value.toLocaleString()
    return String(value)
  }

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="overflow-auto max-h-[400px]">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50">
                  {tableColumns.map((col) => (
                    <th
                      key={col.key}
                      className={`px-4 py-3 text-left font-medium text-muted-foreground ${
                        col.sortable ? "cursor-pointer hover:bg-muted/80" : ""
                      }`}
                      onClick={() => col.sortable && handleSort(col.key)}
                    >
                      <div className="flex items-center gap-2">
                        {col.label}
                        {col.sortable && sortKey === col.key && (
                          <span className="text-xs">
                            {sortOrder === "asc" ? (
                              <ChevronUp className="h-4 w-4 inline" />
                            ) : (
                              <ChevronDown className="h-4 w-4 inline" />
                            )}
                          </span>
                        )}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y">
                {paginatedData.map((row, index) => (
                  <tr
                    key={index}
                    className="hover:bg-muted/50 transition-colors"
                  >
                    {tableColumns.map((col) => (
                      <td key={col.key} className="px-4 py-3">
                        {formatValue(row[col.key], 'formatter' in col ? col.formatter : undefined)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {showPagination && totalPages > 1 && (
            <div className="flex items-center justify-between">
              <div className="text-sm text-muted-foreground">
                共 {sortedData.length} 条，第 {currentPage} / {totalPages} 页
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                  disabled={currentPage === 1}
                  className="px-3 py-1 rounded border disabled:opacity-50 disabled:cursor-not-allowed hover:bg-muted"
                >
                  上一页
                </button>
                <button
                  onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                  disabled={currentPage === totalPages}
                  className="px-3 py-1 rounded border disabled:opacity-50 disabled:cursor-not-allowed hover:bg-muted"
                >
                  下一页
                </button>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}




