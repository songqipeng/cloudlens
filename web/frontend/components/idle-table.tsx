"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { useLocale } from "@/contexts/locale-context"

interface IdleInstance {
    instance_id: string
    name: string
    region: string
    spec: string
    reasons: string[]
}

export function IdleTable({ data }: { data: IdleInstance[] }) {
    const { t, locale } = useLocale()
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
      <Card>
        <CardHeader className="pb-4">
          <CardTitle className="text-xl font-semibold">{t.dashboard.idleResources}</CardTitle>
          <CardDescription className="mt-1">{t.dashboard.idleResourcesTable}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
            <div className="w-16 h-16 mb-4 rounded-full bg-emerald-500/10 flex items-center justify-center">
              <svg className="w-8 h-8 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <p className="text-base font-medium text-foreground">{locale === 'zh' ? '暂无闲置资源' : 'No Idle Resources'}</p>
            <p className="text-sm mt-1 opacity-70">{locale === 'zh' ? '所有资源运行正常' : 'All resources are running normally'}</p>
          </div>
        </CardContent>
      </Card>
    )
  }

    return (
        <Card className="animate-fade-in">
            <CardHeader className="pb-4">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                    <div>
                        <CardTitle className="text-xl font-semibold">{t.dashboard.idleResources}</CardTitle>
                        <CardDescription className="mt-1.5">
                            {locale === 'zh' 
                                ? `共发现 ${data.length} 个闲置实例，建议及时处理`
                                : `Found ${data.length} idle instances, suggest handling soon`}
                        </CardDescription>
                    </div>
                    <div className="relative">
                        <input
                            type="text"
                            placeholder={locale === 'zh' ? '搜索资源名称、ID或区域...' : 'Search by name, ID or region...'}
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="w-full sm:w-72 px-4 py-2.5 pl-11 rounded-lg border border-input/50 bg-background/60 backdrop-blur-sm text-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all duration-200 shadow-sm hover:border-primary/30"
                        />
                        <svg className="absolute left-3.5 top-3 h-4 w-4 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                <div className="h-[550px] overflow-y-auto rounded-lg border border-border/50 bg-background/40 backdrop-blur-sm relative shadow-inner">
                    <table className="w-full text-sm text-left relative">
                        <thead className="text-xs text-muted-foreground uppercase bg-gradient-to-r from-muted/90 to-muted/70 sticky top-0 z-10 backdrop-blur-md border-b border-border/50">
                            <tr>
                                <th 
                                    className="px-6 py-4 font-semibold cursor-pointer hover:bg-muted/70 transition-colors duration-200"
                                    onClick={() => handleSort("name")}
                                >
                                    <div className="flex items-center gap-2">
                                        {locale === 'zh' ? '资源信息' : 'Resource Info'}
                                        {sortBy === "name" && (
                                            <span className="text-primary font-bold">{sortOrder === "asc" ? "↑" : "↓"}</span>
                                        )}
                                    </div>
                                </th>
                                <th 
                                    className="px-6 py-4 font-semibold cursor-pointer hover:bg-muted/70 transition-colors duration-200"
                                    onClick={() => handleSort("spec")}
                                >
                                    <div className="flex items-center gap-2">
                                        {locale === 'zh' ? '规格' : 'Spec'}
                                        {sortBy === "spec" && (
                                            <span className="text-primary font-bold">{sortOrder === "asc" ? "↑" : "↓"}</span>
                                        )}
                                    </div>
                                </th>
                                <th 
                                    className="px-6 py-4 font-semibold cursor-pointer hover:bg-muted/70 transition-colors duration-200"
                                    onClick={() => handleSort("region")}
                                >
                                    <div className="flex items-center gap-2">
                                        {t.resources.region}
                                        {sortBy === "region" && (
                                            <span className="text-primary font-bold">{sortOrder === "asc" ? "↑" : "↓"}</span>
                                        )}
                                    </div>
                                </th>
                                <th className="px-6 py-4 font-semibold">{locale === 'zh' ? '闲置原因' : 'Idle Reason'}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border/20">
                            {filtered.map((item) => (
                                <tr key={item.instance_id} className="hover:bg-primary/8 transition-all duration-200 group border-b border-border/10">
                                    <td className="px-6 py-4">
                                        <div className="font-semibold text-foreground group-hover:text-primary transition-colors duration-200">{item.name || (locale === 'zh' ? '未命名' : 'Unnamed')}</div>
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
                                            {item.reasons[0] || (locale === 'zh' ? '未知原因' : 'Unknown')}
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

