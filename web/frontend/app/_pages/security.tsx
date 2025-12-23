"use client"

import { useEffect, useMemo, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { StatusBadge } from "@/components/ui/badge"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { useRouter } from "next/navigation"
import { AlertTriangle, Shield, Lock, Tag, Server, Globe, Zap, Network } from "lucide-react"
import { useAccount } from "@/contexts/account-context"
import { useLocale } from "@/contexts/locale-context"
import { apiGet } from "@/lib/api"

export default function SecurityPage() {
  const router = useRouter()
  const { currentAccount } = useAccount()
  const { t } = useLocale()
  const [overview, setOverview] = useState<any>(null)
  const [checks, setChecks] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedChecks, setExpandedChecks] = useState<Set<string>>(new Set())

  const base = useMemo(() => {
    return currentAccount ? `/a/${encodeURIComponent(currentAccount)}` : ""
  }, [currentAccount])

  useEffect(() => {
    if (!currentAccount) {
      setLoading(false)
      return
    }
    fetchData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentAccount])

  const fetchData = async () => {
    if (!currentAccount) return

    try {
      const [overviewData, checksData] = await Promise.all([
        apiGet("/security/overview").catch(() => ({ data: null })),
        apiGet("/security/checks").catch(() => ({ data: [] })),
      ])

      if (overviewData.data) {
        setOverview(overviewData.data)
      }

      if (checksData.data) {
        setChecks(checksData.data || [])
      }
    } catch (e) {
      console.error("Failed to fetch security data:", e)
    } finally {
      setLoading(false)
    }
  }

  const toggleCheck = (type: string) => {
    const newExpanded = new Set(expandedChecks)
    if (newExpanded.has(type)) {
      newExpanded.delete(type)
    } else {
      newExpanded.add(type)
    }
    setExpandedChecks(newExpanded)
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "CRITICAL":
        return "text-red-600 bg-red-500/10 border-red-500/20"
      case "HIGH":
        return "text-red-500 bg-red-500/10 border-red-500/20"
      case "MEDIUM":
        return "text-yellow-500 bg-yellow-500/10 border-yellow-500/20"
      case "LOW":
        return "text-blue-500 bg-blue-500/10 border-blue-500/20"
      default:
        return "text-green-500 bg-green-500/10 border-green-500/20"
    }
  }

  const getCheckIcon = (type: string) => {
    switch (type) {
      case "public_exposure":
        return <Globe className="w-5 h-5" />
      case "stopped_instances":
        return <Server className="w-5 h-5" />
      case "tag_coverage":
        return <Tag className="w-5 h-5" />
      case "disk_encryption":
        return <Lock className="w-5 h-5" />
      case "preemptible_instances":
        return <Zap className="w-5 h-5" />
      case "eip_usage":
        return <Network className="w-5 h-5" />
      default:
        return <Shield className="w-5 h-5" />
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-green-500"
    if (score >= 60) return "text-yellow-500"
    return "text-red-500"
  }

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 max-w-[1600px] mx-auto space-y-6">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">{t.security.title}</h2>
          <p className="text-muted-foreground mt-1">{t.security.description}</p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-40">
            <div className="animate-pulse">{t.common.loading}</div>
          </div>
        ) : (
          <>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <Card className="glass border border-border/50 hover:shadow-xl transition-all">
                <CardHeader>
                  <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
                    <Shield className="w-4 h-4" />
                    {t.security.securityScore}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className={`text-4xl font-bold ${getScoreColor(overview?.security_score || 0)}`}>
                    {overview?.security_score || 0}
                    <span className="text-lg text-muted-foreground">/100</span>
                  </div>
                  {overview?.score_deductions && overview.score_deductions.length > 0 && (
                    <div className="mt-2 text-xs text-muted-foreground">
                      {overview.score_deductions.slice(0, 2).map((d: any, i: number) => (
                        <div key={i}>
                          -{d.deduction}{t.security.points}: {d.reason}
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card className="glass border border-border/50 hover:shadow-xl transition-all">
                <CardHeader>
                  <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
                    <Globe className="w-4 h-4" />
                    {t.security.publicExposure}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-red-500">{overview?.exposed_count || 0}</div>
                  <p className="text-xs text-muted-foreground mt-1">{t.security.highRiskResources}</p>
                </CardContent>
              </Card>

              <Card className="glass border border-border/50 hover:shadow-xl transition-all">
                <CardHeader>
                  <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
                    <Lock className="w-4 h-4" />
                    {t.security.diskEncryptionRate}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{overview?.encryption_rate?.toFixed(1) || 0}%</div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {overview?.encrypted_count || 0} / {overview?.encrypted_count + overview?.unencrypted_count || 0} {t.security.encrypted}
                  </p>
                </CardContent>
              </Card>

              <Card className="glass border border-border/50 hover:shadow-xl transition-all">
                <CardHeader>
                  <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
                    <Tag className="w-4 h-4" />
                    {t.security.tagCoverage}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{overview?.tag_coverage?.toFixed(1) || 0}%</div>
                  <p className="text-xs text-muted-foreground mt-1">{overview?.missing_tags_count || 0} {t.security.resourcesMissingTags}</p>
                </CardContent>
              </Card>
            </div>

            {overview?.suggestions && overview.suggestions.length > 0 && (
              <Card className="glass border border-border/50 shadow-xl">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-yellow-500" />
                    {t.security.securityImprovements}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {overview.suggestions.map((suggestion: string, idx: number) => (
                      <div key={idx} className="p-3 bg-muted/30 rounded-lg text-sm">
                        {suggestion}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            <Card className="glass border border-border/50 shadow-xl">
              <CardHeader>
                <CardTitle>{t.security.detailedResults}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {checks.map((check, idx) => (
                    <div
                      key={idx}
                      className={`border rounded-xl overflow-hidden transition-all ${
                        check.status === "failed"
                          ? "border-red-500/30 bg-red-500/5"
                          : check.status === "warning"
                            ? "border-yellow-500/30 bg-yellow-500/5"
                            : "border-green-500/30 bg-green-500/5"
                      }`}
                    >
                      <div className="p-4 cursor-pointer hover:bg-muted/30 transition-colors" onClick={() => toggleCheck(check.type)}>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className={`p-2 rounded-lg ${getSeverityColor(check.severity || "INFO")}`}>{getCheckIcon(check.type)}</div>
                            <div>
                              <div className="font-semibold text-base">{check.title || check.type}</div>
                              <div className="text-sm text-muted-foreground mt-0.5">{check.description}</div>
                            </div>
                          </div>
                          <div className="flex items-center gap-3">
                            {check.count !== undefined && (
                              <div className="text-sm font-medium">
                                {t.security.foundIssues} <span className="text-primary">{check.count}</span> {t.security.issues}
                              </div>
                            )}
                            {check.coverage !== undefined && (
                              <div className="text-sm font-medium">
                                {t.security.coverage}: <span className="text-primary">{check.coverage}%</span>
                              </div>
                            )}
                            {check.encryption_rate !== undefined && (
                              <div className="text-sm font-medium">
                                {t.security.encryptionRate}: <span className="text-primary">{check.encryption_rate}%</span>
                              </div>
                            )}
                            <StatusBadge status={check.status} />
                            <svg
                              className={`w-5 h-5 text-muted-foreground transition-transform ${expandedChecks.has(check.type) ? "rotate-180" : ""}`}
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                          </div>
                        </div>
                      </div>

                      {expandedChecks.has(check.type) && (
                        <div className="border-t border-border/50 p-4 bg-background/50">
                          {check.recommendation && (
                            <div className="mb-4 p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                              <div className="text-sm font-medium text-blue-400 mb-1">💡 {t.security.suggestion}</div>
                              <div className="text-sm text-muted-foreground">{check.recommendation}</div>
                            </div>
                          )}

                          {check.resources && check.resources.length > 0 && (
                            <div>
                              <div className="text-sm font-medium mb-2">{t.security.problemResources} ({check.resources.length}):</div>
                              <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
                                {check.resources.map((resource: any, rIdx: number) => (
                                  <div
                                    key={rIdx}
                                    className="p-2 bg-muted/30 rounded-lg text-xs hover:bg-muted/50 transition-colors cursor-pointer"
                                    onClick={() => {
                                      if (!base) return
                                      if (resource.id) router.push(`${base}/resources/${resource.id}`)
                                    }}
                                  >
                                    <div className="font-medium truncate">{resource.name || resource.id}</div>
                                    <div className="text-muted-foreground truncate">{resource.id}</div>
                                    {resource.public_ips && <div className="text-muted-foreground mt-1">{t.security.ip}: {resource.public_ips.join(", ")}</div>}
                                    {resource.region && <div className="text-muted-foreground">{t.security.region}: {resource.region}</div>}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </DashboardLayout>
  )
}









