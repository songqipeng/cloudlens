"use client"

import { useEffect, useState, useRef } from "react"
import { usePathname, useRouter } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ConfirmModal, Modal } from "@/components/ui/modal"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { useAccount } from "@/contexts/account-context"
import { useLocale } from "@/contexts/locale-context"
import { apiGet, apiDelete, apiPost, apiPut } from "@/lib/api"
import { Eye, EyeOff, Plus, Edit } from "lucide-react"
import { SmartLoadingProgress } from "@/components/loading-progress"

interface Account {
  name: string
  alias?: string  // 别名（可选，用于显示）
  region: string
  provider?: string
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
  const [showEditModal, setShowEditModal] = useState(false)
  const [editingAccount, setEditingAccount] = useState<Account | null>(null)
  const [adding, setAdding] = useState(false)
  const [editing, setEditing] = useState(false)
  const [addError, setAddError] = useState<string | null>(null)
  const [editError, setEditError] = useState<string | null>(null)
  const [showSecret, setShowSecret] = useState(false)
  const loadingStartTime = useRef<number | null>(null)
  const [form, setForm] = useState({
    name: "",
    alias: "",  // 别名
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
      setLoading(true)
      loadingStartTime.current = Date.now()
      const response = await apiGet("/settings/accounts")
      if (response && response.success) {
        setAccounts(response.data || [])
      } else {
        // 兼容旧接口
        const data = await apiGet("/accounts")
        setAccounts(Array.isArray(data) ? data : [])
      }
      await refreshAccountContext()
    } catch (e) {
      console.error("Failed to fetch accounts:", e)
      // 如果新接口失败，尝试旧接口
      try {
        const data = await apiGet("/accounts")
        setAccounts(Array.isArray(data) ? data : [])
      } catch (e2) {
        console.error("Failed to fetch accounts from fallback:", e2)
      }
    } finally {
      setLoading(false)
      setTimeout(() => {
        loadingStartTime.current = null
      }, 500)
    }
  }

  const resetAddForm = () => {
    setAddError(null)
    setAdding(false)
    setShowSecret(false)
    setForm({
      name: "",
      alias: "",
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
    const alias = form.alias.trim() || undefined
    const region = form.region.trim() || "cn-hangzhou"
    const accessKeyId = form.access_key_id.trim()
    const accessKeySecret = form.access_key_secret.trim()

    if (!name) return setAddError(t.accounts.nameRequired)
    if (!accessKeyId) return setAddError(t.accounts.keyIdRequired)
    if (!accessKeySecret) return setAddError(t.accounts.secretRequired)

    setAdding(true)
    try {
      const accountData: any = {
        name,
        provider: form.provider || "aliyun",
        region,
        access_key_id: accessKeyId,
        access_key_secret: accessKeySecret,
      }
      if (alias) {
        accountData.alias = alias
      }
      await apiPost("/settings/accounts", accountData)
      await fetchAccounts()
      setCurrentAccount(name)
      setShowAddModal(false)
      resetAddForm()
      goToAccountSettings(name)
    } catch (e: any) {
      console.error("Failed to add account:", e)
      // 提供更友好的错误信息
      let errorMessage = String(e)
      if (e instanceof Error) {
        errorMessage = e.message
        // 如果是网络错误，提供更详细的提示
        if (e.message.includes("Failed to fetch") || e.message.includes("无法连接到服务器")) {
          errorMessage = "无法连接到后端服务。请确保后端服务正在运行（http://localhost:8000）"
        }
      } else if (e?.detail) {
        // 处理detail对象
        if (typeof e.detail === 'string') {
          errorMessage = e.detail
        } else if (e.detail?.error) {
          errorMessage = e.detail.error
        } else if (e.detail?.message) {
          errorMessage = e.detail.message
        } else if (e.detail?.detail) {
          errorMessage = e.detail.detail
        } else {
          errorMessage = JSON.stringify(e.detail)
        }
      } else if (e?.error) {
        errorMessage = typeof e.error === 'string' ? e.error : JSON.stringify(e.error)
      } else if (e?.message) {
        errorMessage = e.message
      }
      setAddError(errorMessage)
      setAdding(false)
    }
  }

  const handleEdit = (account: Account) => {
    setEditingAccount(account)
    setForm({
      name: account.name,
      alias: account.alias || "",
      provider: account.provider || "aliyun",
      region: account.region,
      access_key_id: account.access_key_id,
      access_key_secret: "", // 不显示现有密钥，需要用户重新输入
    })
    setShowSecret(false)
    setEditError(null)
    setShowEditModal(true)
  }

  const handleUpdate = async () => {
    if (!editingAccount) return
    
    setEditError(null)
    const alias = form.alias.trim() || undefined
    const region = form.region.trim() || "cn-hangzhou"
    const accessKeyId = form.access_key_id.trim()
    const accessKeySecret = form.access_key_secret.trim()

    if (!accessKeyId) return setEditError(t.accounts.keyIdRequired)

    setEditing(true)
    try {
      const updateData: any = {
        provider: form.provider || "aliyun",
        region,
        access_key_id: accessKeyId,
      }
      
      // 添加别名（如果有）
      if (alias !== undefined) {
        updateData.alias = alias
      }
      
      // 只有用户输入了新密钥时才更新
      if (accessKeySecret) {
        updateData.access_key_secret = accessKeySecret
      }
      
      await apiPut(`/settings/accounts/${editingAccount.name}`, updateData)
      await fetchAccounts()
      
      setShowEditModal(false)
      setEditingAccount(null)
      resetAddForm()
    } catch (e: any) {
      console.error("Failed to update account:", e)
      // 提供更友好的错误信息
      let errorMessage = String(e)
      if (e instanceof Error) {
        errorMessage = e.message
        // 如果是网络错误，提供更详细的提示
        if (e.message.includes("Failed to fetch") || e.message.includes("无法连接到服务器")) {
          errorMessage = "无法连接到后端服务。请确保后端服务正在运行（http://localhost:8000）"
        }
      } else if (e?.detail) {
        // 处理detail对象
        if (typeof e.detail === 'string') {
          errorMessage = e.detail
        } else if (e.detail?.error) {
          errorMessage = e.detail.error
        } else if (e.detail?.message) {
          errorMessage = e.detail.message
        } else if (e.detail?.detail) {
          errorMessage = e.detail.detail
        } else {
          errorMessage = JSON.stringify(e.detail)
        }
      } else if (e?.error) {
        errorMessage = typeof e.error === 'string' ? e.error : JSON.stringify(e.error)
      } else if (e?.message) {
        errorMessage = e.message
      }
      setEditError(errorMessage)
      setEditing(false)
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

        {loading && loadingStartTime.current && (
          <SmartLoadingProgress
            message={t.common.loading || "正在加载账号列表..."}
            loading={loading}
            startTime={loadingStartTime.current}
          />
        )}

        <Card className="glass border border-border/50 shadow-xl">
          <CardHeader>
            <CardTitle>{t.accounts.configuredAccounts}</CardTitle>
          </CardHeader>
          <CardContent>
            {loading && !loadingStartTime.current ? (
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
                      <div className="font-semibold text-foreground">
                        {account.alias || account.name}
                        {account.alias && (
                          <span className="text-xs text-muted-foreground ml-2 font-normal">
                            ({account.name})
                          </span>
                        )}
                      </div>
                      <div className="text-sm text-muted-foreground mt-1">{t.accounts.region}: {account.region} | AK: {account.access_key_id.substring(0, 8)}...</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleEdit(account)}
                        className="px-4 py-2 text-sm text-primary hover:bg-primary/10 rounded-lg transition-colors"
                      >
                        {t.common.edit}
                      </button>
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

        {/* 编辑账号模态框 */}
        <Modal
          isOpen={showEditModal}
          onClose={() => {
            setShowEditModal(false)
            setEditingAccount(null)
            resetAddForm()
          }}
          title={t.accounts.editAccount || "编辑账号"}
          size="md"
        >
          <div className="space-y-5">
            <div className="text-sm text-muted-foreground">
              {t.accounts.editAccountDesc || "更新账号配置信息。如果不输入新密钥，将保持现有密钥不变。"}
            </div>

            {editError && (
              <div className="p-3 rounded-lg border border-destructive/30 bg-destructive/10 text-sm text-destructive">
                {editError}
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <div className="text-sm font-medium">{t.accounts.accountName}</div>
                <input
                  value={form.name}
                  disabled
                  className="w-full px-3 py-2.5 rounded-lg border border-border/60 bg-muted/30 text-muted-foreground text-sm cursor-not-allowed"
                />
                <p className="text-xs text-muted-foreground">
                  {t.accounts.accountNameImmutable || "账号名称不可修改，用于数据关联"}
                </p>
              </div>

              <div className="space-y-2">
                <div className="text-sm font-medium">{t.accounts.alias || "显示别名"}</div>
                <input
                  value={form.alias}
                  onChange={(e) => setForm((s) => ({ ...s, alias: e.target.value }))}
                  placeholder={t.accounts.aliasPlaceholder || "可选，用于显示，留空则显示账号名称"}
                  className="w-full px-3 py-2.5 rounded-lg border border-border/60 bg-background focus:outline-none focus:ring-2 focus:ring-primary/30 text-sm"
                />
                <p className="text-xs text-muted-foreground">
                  {t.accounts.aliasNote || "设置别名后，界面将显示别名而不是账号名称，但数据关联仍使用账号名称"}
                </p>
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
                    placeholder={t.accounts.editSecretPlaceholder || "留空则不更新密钥"}
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
                  {t.accounts.editSecretNote || "留空则不更新密钥，输入新密钥将替换现有密钥"}
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => {
                  setShowEditModal(false)
                  setEditingAccount(null)
                  resetAddForm()
                }}
                className="px-4 py-2.5 rounded-lg border border-border hover:bg-muted/40 transition-colors text-sm"
                disabled={editing}
              >
                {t.common.cancel}
              </button>
              <button
                onClick={handleUpdate}
                disabled={editing}
                className="px-5 py-2.5 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {editing ? t.accounts.saving : t.common.save}
              </button>
            </div>
          </div>
        </Modal>

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
                <div className="text-sm font-medium">{t.accounts.alias || "显示别名"}</div>
                <input
                  value={form.alias}
                  onChange={(e) => setForm((s) => ({ ...s, alias: e.target.value }))}
                  placeholder={t.accounts.aliasPlaceholder || "可选，用于显示，留空则显示账号名称"}
                  className="w-full px-3 py-2.5 rounded-lg border border-border/60 bg-background focus:outline-none focus:ring-2 focus:ring-primary/30 text-sm"
                />
                <p className="text-xs text-muted-foreground">
                  {t.accounts.aliasNote || "设置别名后，界面将显示别名而不是账号名称，但数据关联仍使用账号名称"}
                </p>
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











