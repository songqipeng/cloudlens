"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"

interface IdleInstance {
    instance_id: string
    name: string
    region: string
    spec: string
    reasons: string[]
}

export function IdleTable({ data }: { data: IdleInstance[] }) {
    const [search, setSearch] = useState("")
    const [sortBy, setSortBy] = useState<"name" | "region" | "spec" | null>(null)
    const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc")
    
    const handleSort = (field: "name" | "region" | "spec") => {
        if (sortBy === field) {
            setSortOrder(sortOrder === "asc" ? "desc" : "asc")
        } else {
            setSortBy(field)
            setSortOrder("asc")
        }
    }
    
    let filtered = data.filter(item => 
        item.name.toLowerCase().includes(search.toLowerCase()) ||
        item.instance_id.toLowerCase().includes(search.toLowerCase()) ||
        item.region.toLowerCase().includes(search.toLowerCase())
    )
    
    if (sortBy) {
        filtered = [...filtered].sort((a, b) => {
            const aVal = a[sortBy]
            const bVal = b[sortBy]
            const comparison = aVal.localeCompare(bVal)
            return sortOrder === "asc" ? comparison : -comparison
        })
    }
    if (!data || data.length === 0) {
        return (
            <Card className="glass border border-border/50 shadow-xl">
                <CardHeader className="pb-4">
                    <CardTitle className="text-xl font-semibold">闲置资源</CardTitle>
                    <CardDescription className="mt-1">需要关注的低负载资源</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
                        <svg className="w-16 h-16 mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        <p className="text-base">暂无闲置资源</p>
                        <p className="text-sm mt-1 opacity-70">所有资源运行正常</p>
                    </div>
                </CardContent>
            </Card>
        )
    }

    return (
        <Card className="glass border border-border/50 shadow-2xl animate-fade-in">
            <CardHeader className="pb-4">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                    <div>
                        <CardTitle className="text-xl font-semibold">闲置资源</CardTitle>
                        <CardDescription className="mt-1.5">共发现 <span className="text-orange-500 font-semibold">{data.length}</span> 个闲置实例，建议及时处理</CardDescription>
                    </div>
                    <div className="relative">
                        <input
                            type="text"
                            placeholder="搜索资源名称、ID或区域..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="w-full sm:w-72 px-4 py-2.5 pl-11 rounded-xl border border-input/50 bg-background/60 backdrop-blur-sm text-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all shadow-sm"
                        />
                        <svg className="absolute left-3.5 top-3 h-4 w-4 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                <div className="h-[550px] overflow-y-auto rounded-xl border border-border/50 bg-background/40 backdrop-blur-sm relative shadow-inner">
                    <table className="w-full text-sm text-left relative">
                        <thead className="text-xs text-muted-foreground uppercase bg-gradient-to-r from-muted/90 to-muted/70 sticky top-0 z-10 backdrop-blur-md border-b border-border/50">
                            <tr>
                                <th 
                                    className="px-6 py-4 font-semibold cursor-pointer hover:bg-muted/70 transition-colors"
                                    onClick={() => handleSort("name")}
                                >
                                    <div className="flex items-center gap-2">
                                        资源信息
                                        {sortBy === "name" && (
                                            <span className="text-primary font-bold">{sortOrder === "asc" ? "↑" : "↓"}</span>
                                        )}
                                    </div>
                                </th>
                                <th 
                                    className="px-6 py-4 font-semibold cursor-pointer hover:bg-muted/70 transition-colors"
                                    onClick={() => handleSort("spec")}
                                >
                                    <div className="flex items-center gap-2">
                                        规格
                                        {sortBy === "spec" && (
                                            <span className="text-primary font-bold">{sortOrder === "asc" ? "↑" : "↓"}</span>
                                        )}
                                    </div>
                                </th>
                                <th 
                                    className="px-6 py-4 font-semibold cursor-pointer hover:bg-muted/70 transition-colors"
                                    onClick={() => handleSort("region")}
                                >
                                    <div className="flex items-center gap-2">
                                        区域
                                        {sortBy === "region" && (
                                            <span className="text-primary font-bold">{sortOrder === "asc" ? "↑" : "↓"}</span>
                                        )}
                                    </div>
                                </th>
                                <th className="px-6 py-4 font-semibold">闲置原因</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border/20">
                            {filtered.map((item) => (
                                <tr key={item.instance_id} className="hover:bg-primary/8 transition-all duration-200 group border-b border-border/10">
                                    <td className="px-6 py-4">
                                        <div className="font-semibold text-foreground group-hover:text-primary transition-colors">{item.name || '未命名'}</div>
                                        <div className="text-xs text-muted-foreground font-mono mt-1.5 opacity-75">{item.instance_id}</div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className="text-sm text-muted-foreground font-mono bg-muted/30 px-2 py-1 rounded">{item.spec}</span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className="text-sm text-muted-foreground">{item.region}</span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className="inline-flex items-center px-3 py-1.5 rounded-full text-xs font-semibold bg-yellow-500/15 text-yellow-500 border border-yellow-500/30 shadow-sm">
                                            {item.reasons[0] || '未知原因'}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </CardContent>
        </Card>
    )
}

