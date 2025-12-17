"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { StatusBadge } from "@/components/ui/badge"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { apiGet } from "@/lib/api"

export default function CISPage() {
  const [cisData, setCisData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchCIS()
  }, [])

  const fetchCIS = async () => {
    try {
      const data = await apiGet("/security/cis")
      if (data.success) {
        setCisData(data.data)
      }
    } catch (e) {
      console.error("Failed to fetch CIS data:", e)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-pulse">加载中...</div>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 max-w-[1600px] mx-auto space-y-6">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">CIS合规检查</h2>
          <p className="text-muted-foreground mt-1">CIS Benchmark合规性检查</p>
        </div>

        {cisData?.message ? (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">{cisData.message}</CardContent>
          </Card>
        ) : (
          <>
            <Card>
              <CardHeader>
                <CardTitle>合规度</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-4xl font-bold">{cisData?.compliance_rate || 0}%</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>检查项</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {cisData?.checks?.map((check: any, idx: number) => (
                    <div key={idx} className="p-4 border rounded-md">
                      <div className="flex items-center justify-between">
                        <div className="font-medium">{check.name || check.type}</div>
                        <StatusBadge status={check.status || "pending"} />
                      </div>
                      {check.description && <div className="text-sm text-muted-foreground mt-2">{check.description}</div>}
                    </div>
                  )) || (
                    <div className="text-center py-8 text-muted-foreground">暂无检查项</div>
                  )}
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </DashboardLayout>
  )
}





