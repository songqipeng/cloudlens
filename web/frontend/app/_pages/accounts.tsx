"use client"

import { useEffect, useState } from "react"
import { usePathname, useRouter } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ConfirmModal, Modal } from "@/components/ui/modal"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { useAccount } from "@/contexts/account-context"
import { useLocale } from "@/contexts/locale-context"
import { apiGet, apiDelete, apiPost } from "@/lib/api"
import { Eye, EyeOff, Plus } from "lucide-react"

interface Account {
  name: string
  region: string
  access_key_id: string
}

export default function AccountsPage() {
  const { refreshAccounts: refreshAccountContext, setCurrentAccount } = useAccount()
  const { t } = useLocale()
  const router = useRouter()
  const pathname = usePathname()
  const [accounts, setAccounts] = useState<Account[]>([])
  const [loading, setLoading] = useState(true)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null)

  const [showAddModal, setShowAddModal] = useState(false)
  const [adding, setAdding] = useState(false)
  const [addError, setAddError] = useState<string | null>(null)
  const [showSecret, setShowSecret] = useState(false)
  const [form, setForm] = useState({
    name: "",
    provider: "aliyun",
    region: "cn-hangzhou",
    access_key_id: "",
    access_key_secret: "",
  })

  useEffect(() => {
    fetchAccounts()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const fetchAccounts = async () => {
    try {
      const data = await apiGet("/accounts")
      setAccounts(data)
      await refreshAccountContext()
    } catch (e) {
      console.error("Failed to fetch accounts:", e)
    } finally {
      setLoading(false)
    }
  }

  const resetAddForm = () => {
    setAddError(null)
    setAdding(false)
    setShowSecret(false)
    setForm({
      name: "",
      provider: "aliyun",
      region: "cn-hangzhou",
      access_key_id: "",
      access_key_secret: "",
    })
  }

  const goToAccountSettings = (accountName: string) => {
    const encoded = encodeURIComponent(accountName)
    if (pathname?.startsWith("/a/")) {
      const parts = pathname.split("/").filter(Boolean) // ["a", "{old}", "settings", "accounts"]
      if (parts.length >= 2 && parts[0] === "a") {
        parts[1] = encoded
        router.replace("/" + parts.join("/"))
        return
      }
    }
    router.replace(`/a/${encoded}/settings/accounts`)
  }

  const handleAdd = async () => {
    setAddError(null)
    const name = form.name.trim()
    const region = form.region.trim() || "cn-hangzhou"
    const accessKeyId = form.access_key_id.trim()
    const accessKeySecret = form.access_key_secret.trim()

    if (!name) return setAddError(t.accounts.nameRequired)
    if (!accessKeyId) return setAddError(t.accounts.keyIdRequired)
    if (!accessKeySecret) return setAddError(t.accounts.secretRequired)

    setAdding(true)
    try {
      await apiPost("/settings/accounts", {
        name,
        provider: form.provider || "aliyun",
        region,
        access_key_id: accessKeyId,
        access_key_secret: accessKeySecret,
      })
      await fetchAccounts()
      setCurrentAccount(name)
      setShowAddModal(false)
      resetAddForm()
      goToAccountSettings(name)
    } catch (e) {
      console.error("Failed to add account:", e)
      setAddError(String(e))
      setAdding(false)
    }
  }

  const handleDelete = async () => {
    if (!selectedAccount) return
    try {
      await apiDelete(`/settings/accounts/${selectedAccount}`)
      fetchAccounts()
      setShowDeleteModal(false)
      setSelectedAccount(null)
    } catch (e) {
      console.error("Failed to delete account:", e)
    }
  }

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 max-w-[1600px] mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">{t.accounts.title}</h2>
            <p className="text-muted-foreground mt-1">{t.accounts.description}</p>
          </div>
          <button
            onClick={() => {
              resetAddForm()
              setShowAddModal(true)
            }}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-primary text-primary-foreground rounded-xl text-sm font-medium hover:bg-primary/90 transition-colors shadow-lg shadow-primary/15"
          >
            <Plus className="w-4 h-4" />
            {t.accounts.addAccount}
          </button>
        </div>

        <Card className="glass border border-border/50 shadow-xl">
          <CardHeader>
            <CardTitle>{t.accounts.configuredAccounts}</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center h-40">
                <div className="animate-pulse">{t.common.loading}</div>
              </div>
            ) : accounts.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <svg className="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4v16m8-8H4" />
                </svg>
                <p className="text-base">{t.accounts.noAccounts}</p>
                <p className="text-sm mt-1 opacity-70">{t.accounts.noAccountsDesc}</p>
              </div>
            ) : (
              <div className="space-y-3">
                {accounts.map((account) => (
                  <div
                    key={account.name}
                    className="flex items-center justify-between p-4 border border-border/50 rounded-xl hover:bg-muted/30 transition-all hover:shadow-md"
                  >
                    <div>
                      <div className="font-semibold text-foreground">{account.name}</div>
                      <div className="text-sm text-muted-foreground mt-1">{t.accounts.region}: {account.region} | AK: {account.access_key_id.substring(0, 8)}...</div>
                    </div>
                    <button
                      onClick={() => {
                        setSelectedAccount(account.name)
                        setShowDeleteModal(true)
                      }}
                      className="px-4 py-2 text-sm text-destructive hover:bg-destructive/10 rounded-lg transition-colors"
                    >
                      {t.accounts.delete}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <ConfirmModal
          isOpen={showDeleteModal}
          onClose={() => {
            setShowDeleteModal(false)
            setSelectedAccount(null)
          }}
          onConfirm={handleDelete}
          title={t.accounts.confirmDelete}
          message={t.accounts.confirmDeleteMessage.replace('{account}', selectedAccount || '')}
          confirmText={t.accounts.delete}
          cancelText={t.common.cancel}
          variant="danger"
        />

        <Modal
          isOpen={showAddModal}
          onClose={() => {
            setShowAddModal(false)
            resetAddForm()
          }}
          title={t.accounts.addCloudAccount}
          size="md"
        >
          <div className="space-y-5">
            <div className="text-sm text-muted-foreground">
              {t.accounts.addAccountDesc}
            </div>

            {addError && (
              <div className="p-3 rounded-lg border border-destructive/30 bg-destructive/10 text-sm text-destructive">
                {addError}
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <div className="text-sm font-medium">{t.accounts.accountName}</div>
                <input
                  value={form.name}
                  onChange={(e) => setForm((s) => ({ ...s, name: e.target.value }))}
                  placeholder={t.accounts.accountNamePlaceholder}
                  className="w-full px-3 py-2.5 rounded-lg border border-border/60 bg-background focus:outline-none focus:ring-2 focus:ring-primary/30 text-sm"
                />
              </div>

              <div className="space-y-2">
                <div className="text-sm font-medium">{t.accounts.provider}</div>
                <select
                  value={form.provider}
                  onChange={(e) => setForm((s) => ({ ...s, provider: e.target.value }))}
                  className="w-full px-3 py-2.5 rounded-lg border border-border/60 bg-background focus:outline-none focus:ring-2 focus:ring-primary/30 text-sm"
                >
                  <option value="aliyun">{t.accounts.aliyun}</option>
                  <option value="tencent">{t.accounts.tencent}</option>
                </select>
              </div>

              <div className="space-y-2">
                <div className="text-sm font-medium">{t.accounts.region}</div>
                <input
                  value={form.region}
                  onChange={(e) => setForm((s) => ({ ...s, region: e.target.value }))}
                  placeholder={t.accounts.regionPlaceholder}
                  className="w-full px-3 py-2.5 rounded-lg border border-border/60 bg-background focus:outline-none focus:ring-2 focus:ring-primary/30 text-sm"
                />
              </div>

              <div className="space-y-2">
                <div className="text-sm font-medium">{t.accounts.accessKeyId}</div>
                <input
                  value={form.access_key_id}
                  onChange={(e) => setForm((s) => ({ ...s, access_key_id: e.target.value }))}
                  placeholder="LTAIxxxxxxxxxxxxxxxx"
                  className="w-full px-3 py-2.5 rounded-lg border border-border/60 bg-background focus:outline-none focus:ring-2 focus:ring-primary/30 text-sm font-mono"
                  autoComplete="off"
                />
              </div>

              <div className="space-y-2 md:col-span-2">
                <div className="text-sm font-medium">{t.accounts.accessKeySecret}</div>
                <div className="relative">
                  <input
                    type={showSecret ? "text" : "password"}
                    value={form.access_key_secret}
                    onChange={(e) => setForm((s) => ({ ...s, access_key_secret: e.target.value }))}
                    placeholder={t.accounts.accessKeySecret}
                    className="w-full pr-10 px-3 py-2.5 rounded-lg border border-border/60 bg-background focus:outline-none focus:ring-2 focus:ring-primary/30 text-sm font-mono"
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowSecret((v) => !v)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-md hover:bg-muted/40 text-muted-foreground"
                    title={showSecret ? t.accounts.hide : t.accounts.show}
                  >
                    {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                <div className="text-xs text-muted-foreground">
                  {t.accounts.secretNote}
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => {
                  setShowAddModal(false)
                  resetAddForm()
                }}
                className="px-4 py-2.5 rounded-lg border border-border hover:bg-muted/40 transition-colors text-sm"
                disabled={adding}
              >
                {t.common.cancel}
              </button>
              <button
                onClick={handleAdd}
                disabled={adding}
                className="px-5 py-2.5 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {adding ? t.accounts.saving : t.accounts.saveAndSwitch}
              </button>
            </div>
          </div>
        </Modal>
      </div>
    </DashboardLayout>
  )
}






