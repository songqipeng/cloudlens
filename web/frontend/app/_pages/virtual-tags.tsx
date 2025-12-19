"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { useAccount } from "@/contexts/account-context"
import { apiGet, apiPost, apiPut, apiDelete } from "@/lib/api"
import { Plus, Edit, Trash2, Eye, Search } from "lucide-react"

interface TagRule {
  id?: string
  field: string
  operator: string
  pattern: string
  priority: number
}

interface VirtualTag {
  id: string
  name: string
  tag_key: string
  tag_value: string
  rules: TagRule[]
  priority: number
  created_at?: string
  updated_at?: string
}

export default function VirtualTagsPage() {
  const { currentAccount } = useAccount()
  const { t } = useLocale()
  const [tags, setTags] = useState<VirtualTag[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState("")
  const [editingTag, setEditingTag] = useState<VirtualTag | null>(null)
  const [showPreview, setShowPreview] = useState<string | null>(null)

  useEffect(() => {
    fetchTags()
  }, [])

  const fetchTags = async () => {
    try {
      setLoading(true)
      const response = await apiGet("/virtual-tags")
      if (response.success) {
        setTags(response.data || [])
      }
    } catch (e) {
      console.error("Failed to fetch tags:", e)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (tagId: string) => {
    if (!confirm(t.virtualTags.deleteConfirm)) return
    
    try {
      const response = await apiDelete(`/virtual-tags/${tagId}`)
      if (response.success) {
        await fetchTags()
      }
    } catch (e) {
      toastError(t.virtualTags.deleteFailed)
    }
  }

  const handlePreview = async (tagId: string) => {
    if (!currentAccount) {
      toastError(t.virtualTags.selectAccountFirst)
      return
    }
    
    setShowPreview(tagId)
  }

  const filteredTags = tags.filter(tag => 
    tag.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    tag.tag_key.toLowerCase().includes(searchTerm.toLowerCase()) ||
    tag.tag_value.toLowerCase().includes(searchTerm.toLowerCase())
  )

  if (loading) {
    return (
      <DashboardLayout>
        <div className="p-6 md:p-8 max-w-[1600px] mx-auto">
          <div className="flex items-center justify-center min-h-[400px]">
            <div className="animate-pulse text-muted-foreground">{t.common.loading}</div>
          </div>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 max-w-[1600px] mx-auto space-y-6 animate-fade-in">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">{t.virtualTags.title}</h1>
            <p className="text-muted-foreground mt-1">
              {t.virtualTags.description}
            </p>
          </div>
          <Button
            onClick={() => setEditingTag({ id: "", name: "", tag_key: "", tag_value: "", rules: [], priority: 0 })}
            className="flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            {t.virtualTags.createTag}
          </Button>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder={t.virtualTags.searchPlaceholder}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-input/50 bg-background/60 backdrop-blur-sm text-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all duration-200"
          />
        </div>

        {/* Tags List */}
        {filteredTags.length === 0 ? (
          <Card>
            <CardContent className="py-12">
              <div className="text-center text-muted-foreground">
                <p className="text-lg font-medium mb-2">
                  {searchTerm ? t.virtualTags.noMatchTags : t.virtualTags.noTags}
                </p>
                <p className="text-sm">
                  {searchTerm ? t.virtualTags.tryOtherKeywords : t.virtualTags.noTagsDesc}
                </p>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredTags.map((tag) => (
              <Card key={tag.id} className="hover:shadow-lg transition-all duration-200 hover:-translate-y-0.5">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <CardTitle className="text-lg mb-1">{tag.name}</CardTitle>
                      <CardDescription className="text-xs">
                        <span className="font-mono bg-muted/30 px-2 py-0.5 rounded">
                          {tag.tag_key}={tag.tag_value}
                        </span>
                      </CardDescription>
                    </div>
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => handlePreview(tag.id)}
                        title={t.virtualTags.previewMatchingResources}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => setEditingTag(tag)}
                        title={t.virtualTags.editTag}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-destructive hover:text-destructive"
                        onClick={() => handleDelete(tag.id)}
                        title={t.common.delete}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="text-xs text-muted-foreground">
                      {t.virtualTags.ruleCount}: <span className="font-semibold text-foreground">{tag.rules.length}</span>
                    </div>
                    {tag.rules.length > 0 && (
                      <div className="text-xs space-y-1">
                        {tag.rules.slice(0, 2).map((rule, idx) => (
                          <div key={idx} className="bg-muted/30 px-2 py-1 rounded text-xs font-mono">
                            {rule.field} {rule.operator} "{rule.pattern}"
                          </div>
                        ))}
                        {tag.rules.length > 2 && (
                          <div className="text-muted-foreground">+{tag.rules.length - 2} {t.virtualTags.moreRules}</div>
                        )}
                      </div>
                    )}
                    {tag.priority > 0 && (
                      <div className="text-xs text-muted-foreground">
                        {t.virtualTags.priority}: <span className="font-semibold text-foreground">{tag.priority}</span>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Tag Editor Modal */}
        {editingTag && (
          <TagEditor
            tag={editingTag}
            onClose={() => setEditingTag(null)}
            onSave={async () => {
              await fetchTags()
              setEditingTag(null)
            }}
          />
        )}

        {/* Tag Preview Modal */}
        {showPreview && (
          <TagPreview
            tagId={showPreview}
            account={currentAccount}
            onClose={() => setShowPreview(null)}
          />
        )}
      </div>
    </DashboardLayout>
  )
}

// 标签编辑器组件
function TagEditor({ tag, onClose, onSave }: { tag: VirtualTag; onClose: () => void; onSave: () => void }) {
  const [formData, setFormData] = useState({
    name: tag.name,
    tag_key: tag.tag_key,
    tag_value: tag.tag_value,
    priority: tag.priority,
  })
  const [rules, setRules] = useState<TagRule[]>(tag.rules.length > 0 ? tag.rules : [{ field: "name", operator: "contains", pattern: "", priority: 0 }])
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    if (!formData.name || !formData.tag_key || !formData.tag_value) {
      toastError(t.virtualTags.fillRequiredFields)
      return
    }

    if (rules.length === 0 || rules.some(r => !r.pattern)) {
      toastError(t.virtualTags.atLeastOneRule)
      return
    }

    setSaving(true)
    try {
      const payload = {
        name: formData.name,
        tag_key: formData.tag_key,
        tag_value: formData.tag_value,
        rules: rules.map(r => ({
          field: r.field,
          operator: r.operator,
          pattern: r.pattern,
          priority: r.priority,
        })),
        priority: formData.priority,
      }

      if (tag.id) {
        await apiPut(`/virtual-tags/${tag.id}`, payload)
      } else {
        await apiPost("/virtual-tags", payload)
      }
      
      onSave()
    } catch (e) {
      alert("保存失败")
    } finally {
      setSaving(false)
    }
  }

  const addRule = () => {
    setRules([...rules, { field: "name", operator: "contains", pattern: "", priority: 0 }])
  }

  const removeRule = (index: number) => {
    setRules(rules.filter((_, i) => i !== index))
  }

  const updateRule = (index: number, field: keyof TagRule, value: any) => {
    const newRules = [...rules]
    newRules[index] = { ...newRules[index], [field]: value }
    setRules(newRules)
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <CardHeader>
          <CardTitle>{tag.id ? t.virtualTags.editTag : t.virtualTags.createTag}</CardTitle>
          <CardDescription>{t.virtualTags.configureTagRules}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* 基本信息 */}
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">{t.virtualTags.tagName} *</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-4 py-2 rounded-lg border border-input/50 bg-background focus:ring-2 focus:ring-primary/50 focus:border-primary"
                placeholder="例如：生产环境"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-2 block">{t.virtualTags.tagKey} *</label>
                <input
                  type="text"
                  value={formData.tag_key}
                  onChange={(e) => setFormData({ ...formData, tag_key: e.target.value })}
                  className="w-full px-4 py-2 rounded-lg border border-input/50 bg-background focus:ring-2 focus:ring-primary/50 focus:border-primary"
                  placeholder="例如：environment"
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">{t.virtualTags.tagValue} *</label>
                <input
                  type="text"
                  value={formData.tag_value}
                  onChange={(e) => setFormData({ ...formData, tag_value: e.target.value })}
                  className="w-full px-4 py-2 rounded-lg border border-input/50 bg-background focus:ring-2 focus:ring-primary/50 focus:border-primary"
                  placeholder="例如：production"
                />
              </div>
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">{t.virtualTags.priority}</label>
              <input
                type="number"
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) || 0 })}
                className="w-full px-4 py-2 rounded-lg border border-input/50 bg-background focus:ring-2 focus:ring-primary/50 focus:border-primary"
                placeholder="0"
              />
              <p className="text-xs text-muted-foreground mt-1">{t.virtualTags.priorityDesc}</p>
            </div>
          </div>

          {/* 规则列表 */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium">{t.virtualTags.matchingRules} *</label>
              <Button variant="outline" size="sm" onClick={addRule}>
                <Plus className="h-3 w-3 mr-1" />
                {t.virtualTags.addRule}
              </Button>
            </div>
            {rules.map((rule, index) => (
              <div key={index} className="p-4 border border-border/50 rounded-lg space-y-3 bg-muted/20">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{t.virtualTags.rule} {index + 1}</span>
                  {rules.length > 1 && (
                    <Button variant="ghost" size="sm" onClick={() => removeRule(index)}>
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  )}
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="text-xs text-muted-foreground mb-1 block">{t.virtualTags.field}</label>
                    <select
                      value={rule.field}
                      onChange={(e) => updateRule(index, "field", e.target.value)}
                      className="w-full px-3 py-1.5 text-sm rounded-lg border border-input/50 bg-background"
                    >
                      <option value="name">资源名称</option>
                      <option value="region">区域</option>
                      <option value="type">资源类型</option>
                      <option value="instance_id">实例ID</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground mb-1 block">{t.virtualTags.operator}</label>
                    <select
                      value={rule.operator}
                      onChange={(e) => updateRule(index, "operator", e.target.value)}
                      className="w-full px-3 py-1.5 text-sm rounded-lg border border-input/50 bg-background"
                    >
                      <option value="contains">包含</option>
                      <option value="equals">等于</option>
                      <option value="starts_with">开头</option>
                      <option value="ends_with">结尾</option>
                      <option value="regex">正则表达式</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground mb-1 block">{t.virtualTags.pattern}</label>
                    <input
                      type="text"
                      value={rule.pattern}
                      onChange={(e) => updateRule(index, "pattern", e.target.value)}
                      className="w-full px-3 py-1.5 text-sm rounded-lg border border-input/50 bg-background"
                      placeholder="例如：prod"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* 操作按钮 */}
          <div className="flex gap-3 pt-4 border-t">
            <Button variant="outline" onClick={onClose} className="flex-1">
              取消
            </Button>
            <Button onClick={handleSave} disabled={saving} className="flex-1">
              {saving ? "保存中..." : "保存"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// 标签预览组件
function TagPreview({ tagId, account, onClose }: { tagId: string; account: string | null; onClose: () => void }) {
  const [loading, setLoading] = useState(true)
  const [previewData, setPreviewData] = useState<any>(null)
  const [resourceType, setResourceType] = useState("ecs")

  useEffect(() => {
    if (tagId && account) {
      fetchPreview()
    }
  }, [tagId, account, resourceType])

  const fetchPreview = async () => {
    if (!account) return
    
    try {
      setLoading(true)
      const response = await apiPost("/virtual-tags/preview", {
        tag_id: tagId,
        account: account,
        resource_type: resourceType,
      })
      if (response.success) {
        setPreviewData(response.data)
      }
    } catch (e) {
      console.error("Failed to fetch preview:", e)
      toastError(t.virtualTags.previewFailed)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <CardHeader className="flex-shrink-0">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>标签预览</CardTitle>
              <CardDescription className="mt-1">查看匹配的资源列表</CardDescription>
            </div>
            <div className="flex items-center gap-3">
              <select
                value={resourceType}
                onChange={(e) => setResourceType(e.target.value)}
                className="px-3 py-1.5 text-sm rounded-lg border border-input/50 bg-background"
              >
                <option value="ecs">ECS</option>
                <option value="rds">RDS</option>
                <option value="redis">Redis</option>
              </select>
              <Button variant="ghost" size="icon" onClick={onClose}>
                ✕
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-pulse text-muted-foreground">{t.common.loading}</div>
            </div>
          ) : previewData ? (
            <div className="space-y-4">
              {/* 统计信息 */}
              <div className="grid grid-cols-3 gap-4">
                <div className="p-4 bg-muted/30 rounded-lg">
                  <div className="text-sm text-muted-foreground mb-1">匹配资源</div>
                  <div className="text-2xl font-bold">{previewData.matched_count}</div>
                </div>
                <div className="p-4 bg-muted/30 rounded-lg">
                  <div className="text-sm text-muted-foreground mb-1">总资源数</div>
                  <div className="text-2xl font-bold">{previewData.total_count}</div>
                </div>
                <div className="p-4 bg-muted/30 rounded-lg">
                  <div className="text-sm text-muted-foreground mb-1">匹配率</div>
                  <div className="text-2xl font-bold">
                    {previewData.total_count > 0
                      ? ((previewData.matched_count / previewData.total_count) * 100).toFixed(1)
                      : 0}%
                  </div>
                </div>
              </div>

              {/* 规则信息 */}
              {previewData.rules && previewData.rules.length > 0 && (
                <div className="p-4 bg-muted/20 rounded-lg">
                  <div className="text-sm font-medium mb-2">匹配规则</div>
                  <div className="space-y-1">
                    {previewData.rules.map((rule: any, idx: number) => (
                      <div key={idx} className="text-xs font-mono bg-muted/30 px-2 py-1 rounded">
                        {rule.field} {rule.operator} "{rule.pattern}"
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 资源列表 */}
              {previewData.resources && previewData.resources.length > 0 ? (
                <div>
                  <div className="text-sm font-medium mb-3">匹配的资源列表（最多显示100个）</div>
                  <div className="border border-border/50 rounded-lg overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-muted/50">
                        <tr>
                          <th className="px-4 py-2 text-left">资源ID</th>
                          <th className="px-4 py-2 text-left">名称</th>
                          <th className="px-4 py-2 text-left">区域</th>
                          <th className="px-4 py-2 text-left">状态</th>
                          <th className="px-4 py-2 text-left">规格</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/20">
                        {previewData.resources.map((resource: any, idx: number) => (
                          <tr key={idx} className="hover:bg-muted/20">
                            <td className="px-4 py-2 font-mono text-xs">{resource.id}</td>
                            <td className="px-4 py-2">{resource.name || "-"}</td>
                            <td className="px-4 py-2">{resource.region || "-"}</td>
                            <td className="px-4 py-2">{resource.status || "-"}</td>
                            <td className="px-4 py-2">{resource.spec || "-"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <p>没有匹配的资源</p>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <p>预览数据为空</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}


