"use client"

import { useState, useRef, useEffect } from 'react'
import { apiPost } from '@/lib/api'
import { MessageCircle, X, Send, Loader2, Sparkles, ChevronDown, Zap, Trash2, Minimize2 } from 'lucide-react'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at?: string
}

interface ChatResponse {
  message: string
  session_id: string
  usage: {
    input_tokens: number
    output_tokens: number
    total_tokens: number
  }
  model: string
}

interface ModelConfig {
  id: string
  name: string
  description: string
  icon: string
}

const AVAILABLE_MODELS: ModelConfig[] = [
  { id: 'claude', name: 'Claude 3.5 Sonnet', description: '强大的推理和分析能力', icon: '🧠' },
  { id: 'openai', name: 'GPT-4', description: '通用对话和问答', icon: '💬' },
  { id: 'deepseek', name: 'DeepSeek', description: '高性价比AI模型', icon: '⚡' },
]

export function AIChatbot() {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [selectedModel, setSelectedModel] = useState('deepseek')  // 默认使用DeepSeek
  const [showModelSelector, setShowModelSelector] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // 滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    if (isOpen && messages.length > 0) {
      scrollToBottom()
    }
  }, [messages, isOpen])

  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus()
      
      // 检查是否有旧的错误消息，如果有且是API配置错误，提示用户清空
      const lastMessage = messages[messages.length - 1]
      if (lastMessage && lastMessage.role === 'assistant' && 
          (lastMessage.content.includes('AI服务暂时不可用') || 
           lastMessage.content.includes('API配置') ||
           lastMessage.content.includes('认证失败'))) {
        // 不自动清除，让用户手动清除（避免误删重要消息）
        // 但可以在控制台提示
        console.log('💡 检测到旧的错误消息，建议点击清空按钮清除后重新发送消息')
      }
    }
  }, [isOpen, messages])

  // 发送消息
  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      // 从 URL 获取当前账号
      const pathname = window.location.pathname || ""
      let currentAccount: string | null = null
      if (pathname.startsWith("/a/")) {
        const parts = pathname.split("/").filter(Boolean)
        if (parts.length >= 2 && parts[0] === "a" && parts[1]) {
          currentAccount = decodeURIComponent(parts[1])
        }
      }
      if (!currentAccount) {
        currentAccount = localStorage.getItem("currentAccount")
      }

      const response = await apiPost<ChatResponse>(
        '/v1/chatbot/chat',
        {
          messages: [{ role: 'user', content: userMessage.content }],
          session_id: sessionId,
          account: currentAccount,  // 传递当前账号
          provider: selectedModel,
          temperature: 0.7,
          max_tokens: 2000
        },
        currentAccount ? { account: currentAccount } : undefined,  // 显式传递 account 参数
        {
          timeout: 120000,  // AI Chatbot请求需要更长时间（120秒），因为需要获取上下文和调用LLM
          retries: 1  // 不重试，避免重复请求
        }
      )

      console.log('[AI Chatbot] 收到响应:', {
        hasMessage: !!response.message,
        messageLength: response.message?.length,
        session_id: response.session_id
      })

      setSessionId(response.session_id)

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.message
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error: any) {
      console.error('[AI Chatbot] 发送消息失败:', error)
      // 解析错误信息，给出可操作提示
      let errorContent = '抱歉，AI服务暂时不可用。请检查API配置或稍后重试。'
      if (error?.detail?.message) {
        const detailMsg = error.detail.message
        if (detailMsg.includes('401') || detailMsg.includes('Authentication') || detailMsg.includes('invalid')) {
          errorContent = '❌ API密钥认证失败\n\n可能的原因：\n1. API密钥无效或已过期\n2. API密钥格式不正确\n3. 请到设置页面重新配置API密钥\n\n💡 提示：\n- 访问"设置" → "AI 模型配置"重新输入有效的API密钥\n- 配置后，点击右上角🗑️按钮清空此错误消息，然后重新发送'
        } else if (detailMsg.includes('429') || detailMsg.includes('rate limit')) {
          errorContent = '⚠️ 请求频率过高，请稍后再试'
        } else if (detailMsg.includes('500') || detailMsg.includes('Internal')) {
          errorContent = '❌ 服务器内部错误，请稍后重试'
        } else {
          errorContent = `❌ 错误：${detailMsg.substring(0, 200)}\n\n💡 如果已重新配置API密钥，请点击右上角🗑️按钮清空此消息后重试`
        }
      } else if (error?.message) {
        errorContent = `❌ ${error.message}\n\n💡 如果已重新配置API密钥，请点击右上角🗑️按钮清空此消息后重试`
      } else if (error?.detail) {
        const detailStr = JSON.stringify(error.detail)
        errorContent = `❌ 请求失败\n\n错误详情：${detailStr.substring(0, 300)}\n\n💡 如果已重新配置API密钥，请点击右上角🗑️按钮清空此消息后重试`
      }

      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: errorContent
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  // 处理键盘事件
  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // 快速问题
  const quickQuestions = [
    { icon: '📊', text: '为什么这个月成本提升了10%？', category: '成本分析' },
    { icon: '💤', text: '有哪些闲置资源可以优化？', category: '资源优化' },
    { icon: '📈', text: '帮我分析一下最近的成本趋势', category: '趋势分析' },
    { icon: '🔮', text: '预测下个月的成本', category: '成本预测' }
  ]

  const handleQuickQuestion = (question: string) => {
    setInput(question)
    setTimeout(() => {
      handleSend()
    }, 100)
  }

  // 清空对话
  const handleClearChat = () => {
    setMessages([])
    setSessionId(null)
  }

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-20 sm:bottom-8 right-4 sm:right-8 z-[100] group"
        aria-label="打开AI助手"
      >
        <div className="relative">
          {/* 光晕效果 */}
          <div className="absolute inset-0 rounded-full bg-gradient-to-r from-blue-500 to-cyan-500 opacity-75 blur-xl group-hover:opacity-100 transition-opacity duration-300" />

          {/* 主按钮 - 移动端稍小 */}
          <div className="relative bg-gradient-to-br from-blue-600 via-blue-500 to-cyan-500 rounded-full p-3.5 sm:p-5 shadow-2xl transform transition-all duration-300 hover:scale-110 hover:rotate-12">
            <Sparkles className="w-5 h-5 sm:w-7 sm:h-7 text-white" />
          </div>

          {/* 脉冲动画 */}
          <div className="absolute inset-0 rounded-full bg-blue-500 animate-ping opacity-20" />
        </div>

        {/* 提示文字 - 仅桌面端显示 */}
        <div className="hidden sm:block absolute right-full mr-4 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none">
          <div className="bg-gradient-to-r from-blue-600 to-cyan-600 text-white px-4 py-2 rounded-lg shadow-lg whitespace-nowrap text-sm font-medium">
            CloudLens AI 助手
            <div className="absolute left-full top-1/2 -translate-y-1/2 border-8 border-transparent border-l-blue-600" />
          </div>
        </div>
      </button>
    )
  }

  return (
    <div
      className="fixed inset-4 sm:inset-auto sm:bottom-8 sm:right-8 z-[100] flex flex-col transition-all duration-300"
      style={{ maxWidth: '100%', maxHeight: '100%' }}
    >
      {/* 移动端全屏容器，桌面端固定尺寸 */}
      <div className="relative flex flex-col h-full sm:w-[480px] sm:h-[680px] rounded-2xl border border-white/10 bg-gradient-to-b from-slate-900/95 to-slate-950/95 backdrop-blur-xl shadow-2xl overflow-hidden">
        {/* 顶部渐变装饰 */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-500 via-cyan-500 to-blue-500" />

        {/* 头部 */}
        <div className="relative p-5 border-b border-white/10 bg-gradient-to-r from-blue-500/10 via-cyan-500/10 to-blue-500/10">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 blur opacity-50" />
                <div className="relative w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-cyan-600 flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
              </div>
              <div>
                <h3 className="font-bold text-white text-base">CloudLens AI</h3>
                <p className="text-xs text-slate-400">智能云治理助手</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {/* 模型选择器 */}
              <div className="relative">
                <button
                  onClick={() => setShowModelSelector(!showModelSelector)}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 transition-all text-xs text-slate-300 hover:text-white"
                >
                  <span>{AVAILABLE_MODELS.find(m => m.id === selectedModel)?.icon}</span>
                  <ChevronDown className={`w-3 h-3 transition-transform ${showModelSelector ? 'rotate-180' : ''}`} />
                </button>

                {showModelSelector && (
                  <>
                    <div className="fixed inset-0 z-40" onClick={() => setShowModelSelector(false)} />
                    <div className="absolute top-full right-0 mt-2 w-72 rounded-xl bg-slate-900/95 backdrop-blur-xl border border-white/10 shadow-2xl overflow-hidden z-50">
                      {AVAILABLE_MODELS.map((model) => (
                        <button
                          key={model.id}
                          onClick={() => {
                            setSelectedModel(model.id)
                            setShowModelSelector(false)
                          }}
                          className={`w-full flex items-start gap-3 p-3 hover:bg-white/5 transition-all border-b border-white/5 last:border-0 ${
                            selectedModel === model.id ? 'bg-blue-500/10' : ''
                          }`}
                        >
                          <span className="text-2xl">{model.icon}</span>
                          <div className="flex-1 text-left">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-white text-sm">{model.name}</span>
                              {selectedModel === model.id && (
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500 text-white">使用中</span>
                              )}
                            </div>
                            <p className="text-xs text-slate-400 mt-0.5">{model.description}</p>
                          </div>
                        </button>
                      ))}
                    </div>
                  </>
                )}
              </div>

              {/* 清空对话按钮 */}
              {messages.length > 0 && (
                <button
                  onClick={handleClearChat}
                  className="p-2 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white transition-all"
                  aria-label="清空对话"
                  title="清空对话"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}

              <button
                onClick={() => setIsOpen(false)}
                className="p-2 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white transition-all"
                aria-label="最小化"
                title="最小化"
              >
                <Minimize2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* 移除了设置面板 - API 配置已移到设置页面 */}

        {/* 消息列表 */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {messages.length === 0 ? (
            <div className="text-center py-8">
              <div className="relative inline-flex mb-6">
                <div className="absolute inset-0 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 blur-xl opacity-50" />
                <div className="relative w-20 h-20 rounded-full bg-gradient-to-br from-blue-600 to-cyan-600 flex items-center justify-center">
                  <Sparkles className="w-10 h-10 text-white" />
                </div>
              </div>

              <h4 className="text-lg font-bold text-white mb-2">CloudLens AI 智能助手</h4>
              <p className="text-sm text-slate-400 mb-6 max-w-xs mx-auto">
                我可以帮您分析云资源、优化成本、识别安全风险
              </p>

              <div className="space-y-2 max-w-md mx-auto">
                <p className="text-xs text-slate-500 mb-3">✨ 试试问我：</p>
                {quickQuestions.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => handleQuickQuestion(q.text)}
                    className="group w-full flex items-start gap-3 p-3 bg-gradient-to-r from-white/5 to-white/0 hover:from-blue-500/20 hover:to-cyan-500/20 border border-white/10 hover:border-blue-500/30 rounded-xl transition-all duration-300 text-left"
                  >
                    <span className="text-xl flex-shrink-0 mt-0.5">{q.icon}</span>
                    <div className="flex-1 min-w-0">
                      <span className="text-xs text-blue-400 font-medium">{q.category}</span>
                      <p className="text-sm text-slate-300 group-hover:text-white transition-colors mt-0.5">
                        {q.text}
                      </p>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                      msg.role === 'user'
                        ? 'bg-gradient-to-br from-blue-600 to-cyan-600 text-white shadow-lg shadow-blue-500/20'
                        : 'bg-white/5 text-slate-200 border border-white/10'
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-white/5 border border-white/10 rounded-2xl px-4 py-3 flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                    <span className="text-sm text-slate-400">AI 正在思考...</span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* 输入区域 */}
        <div className="p-5 border-t border-white/10 bg-slate-900/50">
          <div className="flex gap-3">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="输入您的问题... (Enter 发送, Shift+Enter 换行)"
                rows={1}
                className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all text-white placeholder:text-slate-500 resize-none text-sm"
                style={{ minHeight: '48px', maxHeight: '120px' }}
                disabled={loading}
              />
            </div>
            <button
              onClick={handleSend}
              disabled={!input.trim() || loading}
              className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white rounded-xl disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 shadow-lg shadow-blue-500/20 hover:shadow-xl hover:shadow-blue-500/30 disabled:shadow-none flex items-center justify-center group"
              aria-label="发送"
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
              )}
            </button>
          </div>

          <div className="flex items-center justify-between mt-3 text-xs text-slate-500">
            <span>当前模型: {AVAILABLE_MODELS.find(m => m.id === selectedModel)?.name}</span>
            <span className="flex items-center gap-1">
              <Zap className="w-3 h-3" />
              由 AI 驱动
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
