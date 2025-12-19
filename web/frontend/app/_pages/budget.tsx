"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { useAccount } from "@/contexts/account-context"
import { useLocale } from "@/contexts/locale-context"
import { apiGet, apiPost } from "@/lib/api"

export default function BudgetPage() {
  const { currentAccount } = useAccount()
  const { t } = useLocale()
  const [budget, setBudget] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [monthlyBudget, setMonthlyBudget] = useState(0)
  const [annualBudget, setAnnualBudget] = useState(0)

  useEffect(() => {
    if (!currentAccount) {
      setLoading(false)
      return
    }
    fetchBudget()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentAccount])

  const fetchBudget = async () => {
    if (!currentAccount) return

    try {
      const data = await apiGet("/cost/budget")
      if (data.success) {
        setBudget(data.data)
        setMonthlyBudget(data.data.monthly_budget || 0)
        setAnnualBudget(data.data.annual_budget || 0)
      }
    } catch (e) {
      console.error("Failed to fetch budget:", e)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    if (!currentAccount) {
      alert(t.budget.selectAccountFirst)
      return
    }

    setSaving(true)
    try {
      await apiPost("/cost/budget", {
        monthly_budget: monthlyBudget,
        annual_budget: annualBudget,
      })
      alert(t.budget.saveSuccess)
      fetchBudget()
    } catch (e) {
      alert(t.budget.saveFailed)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-pulse">{t.common.loading}</div>
        </div>
      </DashboardLayout>
    )
  }

  const usageRate = budget?.current_month_spent && budget?.monthly_budget ? (budget.current_month_spent / budget.monthly_budget) * 100 : 0

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 max-w-[1600px] mx-auto space-y-6">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">{t.budget.title}</h2>
          <p className="text-muted-foreground mt-1">{t.budget.description}</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>{t.budget.budgetSettings}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">{t.budget.monthlyBudget}</label>
              <input
                type="number"
                value={monthlyBudget}
                onChange={(e) => setMonthlyBudget(parseFloat(e.target.value) || 0)}
                className="w-full px-4 py-2.5 rounded-xl border border-input/50 bg-background/60 backdrop-blur-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">{t.budget.annualBudget}</label>
              <input
                type="number"
                value={annualBudget}
                onChange={(e) => setAnnualBudget(parseFloat(e.target.value) || 0)}
                className="w-full px-4 py-2.5 rounded-xl border border-input/50 bg-background/60 backdrop-blur-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              />
            </div>

            <button
              onClick={handleSave}
              disabled={saving}
              className="w-full px-4 py-2.5 bg-primary text-primary-foreground rounded-xl hover:bg-primary/90 disabled:opacity-50 transition-all shadow-lg shadow-primary/20"
            >
              {saving ? t.budget.saving : t.budget.saveBudget}
            </button>
          </CardContent>
        </Card>

        {budget && budget.monthly_budget > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>{t.budget.budgetUsage}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span>{t.budget.currentMonthUsed}</span>
                    <span className="font-semibold">¥{budget.current_month_spent?.toLocaleString() || 0}</span>
                  </div>
                  <div className="w-full bg-muted/50 rounded-full h-3 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        usageRate > 90 ? "bg-red-500" : usageRate > 80 ? "bg-yellow-500" : "bg-green-500"
                      }`}
                      style={{ width: `${Math.min(usageRate, 100)}%` }}
                    />
                  </div>
                  <div className="text-xs text-muted-foreground mt-2">
                    {t.budget.usageRate}: <span className="font-semibold">{usageRate.toFixed(1)}%</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  )
}






