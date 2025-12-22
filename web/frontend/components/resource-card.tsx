"use client"

import React from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Resource } from "@/types/resource"
import { useLocale } from "@/contexts/locale-context"

interface ResourceCardProps {
    resource: Resource
    onClick?: () => void
}

/**
 * 资源卡片组件（使用React.memo优化性能）
 */
export const ResourceCard = React.memo(({ resource, onClick }: ResourceCardProps) => {
    const { t } = useLocale()
    
    const getStatusColor = (status: string) => {
        const statusLower = status?.toLowerCase() || ""
        if (statusLower.includes("running") || statusLower.includes("active")) {
            return "bg-green-500"
        }
        if (statusLower.includes("stopped") || statusLower.includes("inactive")) {
            return "bg-gray-500"
        }
        if (statusLower.includes("error") || statusLower.includes("failed")) {
            return "bg-red-500"
        }
        return "bg-yellow-500"
    }

    return (
        <Card 
            className="hover:shadow-md transition-shadow cursor-pointer"
            onClick={onClick}
        >
            <CardContent className="p-4">
                <div className="flex items-start justify-between">
                    <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                            <h3 className="font-semibold text-sm">{resource.name || resource.id}</h3>
                            <Badge className={getStatusColor(resource.status)}>
                                {resource.status}
                            </Badge>
                        </div>
                        <div className="text-xs text-muted-foreground space-y-1">
                            <div>{t.resources.id || 'ID'}: {resource.id}</div>
                            {resource.region && <div>{t.resources.region || 'Region'}: {resource.region}</div>}
                            {resource.instanceType && <div>{t.resources.spec || 'Spec'}: {resource.instanceType}</div>}
                            {resource.cost && <div>{t.resources.monthlyCost || 'Cost'}: ¥{resource.cost.toFixed(2)}</div>}
                        </div>
                    </div>
                </div>
            </CardContent>
        </Card>
    )
}, (prev, next) => {
    // 自定义比较函数：只在关键字段变化时重新渲染
    return (
        prev.resource.id === next.resource.id &&
        prev.resource.status === next.resource.status &&
        prev.resource.cost === next.resource.cost &&
        prev.onClick === next.onClick
    )
})

ResourceCard.displayName = "ResourceCard"



