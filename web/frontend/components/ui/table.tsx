"use client"

import { useState, ReactNode } from "react"

export interface TableColumn<T> {
    key: string
    label: string
    sortable?: boolean
    render?: (value: any, row: T) => ReactNode
}

export interface TableProps<T> {
    data: T[]
    columns: TableColumn<T>[]
    onSort?: (key: string, order: "asc" | "desc") => void
    onRowClick?: (row: T) => void
    className?: string
}

export function Table<T extends Record<string, any>>({ 
    data, 
    columns, 
    onSort, 
    onRowClick,
    className = ""
}: TableProps<T>) {
    const [sortKey, setSortKey] = useState<string | null>(null)
    const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc")
    
    const handleSort = (key: string) => {
        if (sortKey === key) {
            const newOrder = sortOrder === "asc" ? "desc" : "asc"
            setSortOrder(newOrder)
            onSort?.(key, newOrder)
        } else {
            setSortKey(key)
            setSortOrder("asc")
            onSort?.(key, "asc")
        }
    }
    
    return (
        <div className={`rounded-md border ${className}`}>
            <table className="w-full text-sm">
                <thead>
                    <tr className="border-b bg-muted/50">
                        {columns.map(col => (
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
                                            {sortOrder === "asc" ? "↑" : "↓"}
                                        </span>
                                    )}
                                </div>
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody className="divide-y">
                    {data.map((row, idx) => (
                        <tr
                            key={idx}
                            onClick={() => onRowClick?.(row)}
                            className={`border-b transition-colors ${
                                onRowClick ? "cursor-pointer hover:bg-muted/50" : ""
                            }`}
                        >
                            {columns.map(col => (
                                <td key={col.key} className="px-4 py-3">
                                    {col.render
                                        ? col.render(row[col.key], row)
                                        : row[col.key] ?? "-"}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}





