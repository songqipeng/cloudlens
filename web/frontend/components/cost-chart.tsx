"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { apiGet } from "@/lib/api"

interface ChartData {
    dates: string[]
    costs: number[]
}

interface CostChartProps {
    data: ChartData
    account?: string
}

export function CostChart({ data, account }: CostChartProps) {
    const [days, setDays] = useState(30)
    const [chartData, setChartData] = useState(data)
    
    useEffect(() => {
        let cancelled = false
        async function load() {
            try {
                // 统一使用 apiGet：保证账号参数拼接逻辑一致（必要时也会从 localStorage 兜底）
                const result = await apiGet('/dashboard/trend', { account, days })
                if (!cancelled && result?.chart_data) {
                    setChartData(result.chart_data)
                }
            } catch (e) {
                if (!cancelled) console.error("Failed to fetch trend:", e)
            }
        }
        if (account) load()
        return () => { cancelled = true }
    }, [days, account])
    
    if (!chartData || !chartData.dates) return null;

    const processedData = chartData.dates.map((date, index) => ({
        date: date.substring(5), // MM-DD
        cost: chartData.costs[index]
    }));

    return (
        <Card className="glass border border-border/50 shadow-2xl animate-fade-in">
            <CardHeader className="pb-4">
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle className="text-xl font-semibold">成本趋势</CardTitle>
                        <CardDescription className="mt-1.5">过去 {days} 天的日成本变化趋势</CardDescription>
                    </div>
                    <div className="flex gap-2">
                        {[7, 30, 90].map(d => (
                            <button
                                key={d}
                                onClick={() => setDays(d)}
                                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                                    days === d 
                                        ? 'bg-primary text-primary-foreground shadow-lg shadow-primary/30 scale-105' 
                                        : 'bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground hover:scale-105'
                                }`}
                            >
                                {d}天
                            </button>
                        ))}
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                <div className="h-[450px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={processedData}>
                            <defs>
                                <linearGradient id="colorCost" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" opacity={0.1} stroke="#555" />
                            <XAxis
                                dataKey="date"
                                stroke="#71717a"
                                fontSize={10}
                                tickLine={false}
                                axisLine={false}
                                minTickGap={30}
                            />
                            <YAxis
                                stroke="#71717a"
                                fontSize={10}
                                tickLine={false}
                                axisLine={false}
                                tickFormatter={(value) => `¥${value}`}
                            />
                            <Tooltip
                                contentStyle={{ background: 'rgba(9, 9, 11, 0.9)', border: '1px solid #27272a', borderRadius: '8px', color: '#fff', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.5)' }}
                                itemStyle={{ color: '#fff' }}
                                labelStyle={{ color: '#a1a1aa' }}
                            />
                            <Area
                                type="monotone"
                                dataKey="cost"
                                stroke="#3b82f6"
                                strokeWidth={2}
                                fillOpacity={1}
                                fill="url(#colorCost)"
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            </CardContent>
        </Card>
    )
}
