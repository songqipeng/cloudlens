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
        <div className={`rounded-[12px] border border-[rgba(255,255,255,0.08)] bg-[rgba(15,15,20,0.8)] backdrop-blur-[20px] overflow-hidden ${className}`}>
            <table className="w-full text-sm">
                <thead>
                    <tr className="border-b border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.03)]">
                        {columns.map(col => (
                            <th
                                key={col.key}
                                className={`px-6 py-4 text-left font-semibold text-muted-foreground text-xs uppercase tracking-wider ${
                                    col.sortable ? "cursor-pointer hover:bg-[rgba(255,255,255,0.05)] transition-colors" : ""
                                }`}
                                onClick={() => col.sortable && handleSort(col.key)}
                            >
                                <div className="flex items-center gap-2">
                                    {col.label}
                                    {col.sortable && (
                                        <span className="text-muted-foreground/50">
                                            {sortKey === col.key ? (
                                                sortOrder === "asc" ? (
                                                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                                                    </svg>
                                                ) : (
                                                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                                    </svg>
                                                )
                                            ) : (
                                                <svg className="w-3 h-3 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
                                                </svg>
                                            )}
                                        </span>
                                    )}
                                </div>
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {data.map((row, idx) => (
                        <tr
                            key={idx}
                            onClick={() => onRowClick?.(row)}
                            className={`border-b border-[rgba(255,255,255,0.05)] transition-colors ${
                                idx % 2 === 0 ? "bg-transparent" : "bg-[rgba(255,255,255,0.02)]"
                            } ${
                                onRowClick ? "cursor-pointer hover:bg-[rgba(59,130,246,0.1)]" : ""
                            }`}
                        >
                            {columns.map(col => (
                                <td key={col.key} className="px-6 py-4 text-foreground/90">
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






