"use client"

import { useState, useRef, useEffect } from 'react'
import { apiPost, apiGet } from '@/lib/api'
import { MessageCircle, X, Minimize2, Send, Loader2 } from 'lucide-react'

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

export function AIChatbot() {
  const [isOpen, setIsOpen] = useState(false)
  const [isMinimized, setIsMinimized] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // 滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    if (isOpen && messages.length > 0) {
      scrollToBottom()
    }
  }, [messages, isOpen])

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
      const response = await apiPost<ChatResponse>(
        '/v1/chatbot/chat',
        {
          messages: [{ role: 'user', content: userMessage.content }],
          session_id: sessionId,
          temperature: 0.7,
          max_tokens: 2000
        }
      )

      setSessionId(response.session_id)

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.message
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('发送消息失败:', error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '抱歉，AI服务暂时不可用。请检查API配置或稍后重试。'
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  // 处理键盘事件
  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // 快速问题
  const quickQuestions = [
    '为什么这个月成本提升了10%？',
    '有哪些闲置资源可以优化？',
    '帮我分析一下最近的成本趋势',
    '预测下个月的成本'
  ]

  const handleQuickQuestion = (question: string) => {
    setInput(question)
    setTimeout(() => {
      handleSend()
    }, 100)
  }

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-[100] bg-primary hover:bg-primary/90 text-primary-foreground rounded-full p-4 shadow-lg shadow-primary/25 transition-all duration-200 hover:scale-110 hover:shadow-xl hover:shadow-primary/30"
        aria-label="打开AI助手"
        style={{
          boxShadow: '0 4px 12px rgba(59, 130, 246, 0.25), 0 0 0 1px rgba(59, 130, 246, 0.1)'
        }}
      >
        <MessageCircle className="w-6 h-6" />
      </button>
    )
  }

  return (
    <div
      className={`fixed bottom-6 right-6 z-[100] rounded-[12px] border border-[rgba(255,255,255,0.08)] bg-[rgba(15,15,20,0.95)] backdrop-blur-[20px] shadow-[0_8px_24px_rgba(0,0,0,0.3)] transition-all duration-300 ${
        isMinimized ? 'w-80 h-14' : 'w-96 h-[600px]'
      } flex flex-col`}
      style={{
        boxShadow: '0 8px 24px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(255, 255, 255, 0.08)'
      }}
    >
      {/* 头部 */}
      <div className="flex items-center justify-between p-4 border-b border-[rgba(255,255,255,0.08)] bg-gradient-to-r from-primary/20 to-primary/10">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center">
            <MessageCircle className="w-4 h-4 text-primary" />
          </div>
          <span className="font-semibold text-foreground">CloudLens AI 助手</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsMinimized(!isMinimized)}
            className="hover:bg-muted rounded p-1.5 transition-colors text-muted-foreground hover:text-foreground"
            aria-label={isMinimized ? '展开' : '最小化'}
          >
            <Minimize2 className="w-4 h-4" />
          </button>
          <button
            onClick={() => {
              setIsOpen(false)
              setIsMinimized(false)
            }}
            className="hover:bg-muted rounded p-1.5 transition-colors text-muted-foreground hover:text-foreground"
            aria-label="关闭"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {!isMinimized && (
        <>
          {/* 消息列表 */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[rgba(15,15,20,0.5)]">
            {messages.length === 0 ? (
              <div className="text-center text-muted-foreground py-8">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-primary/10 flex items-center justify-center">
                  <MessageCircle className="w-8 h-8 text-primary" />
                </div>
                <p className="mb-4 text-foreground font-medium">我是CloudLens AI助手，可以帮您：</p>
                <ul className="text-sm text-left max-w-xs mx-auto space-y-2 text-muted-foreground">
                  <li>• 分析成本变化原因</li>
                  <li>• 识别闲置资源</li>
                  <li>• 提供优化建议</li>
                  <li>• 解释账单明细</li>
                </ul>
                <div className="mt-6 space-y-2">
                  <p className="text-xs text-muted-foreground mb-2">快速问题：</p>
                  {quickQuestions.map((q, i) => (
                    <button
                      key={i}
                      onClick={() => handleQuickQuestion(q)}
                      className="block w-full text-left px-3 py-2 text-sm bg-[rgba(15,15,20,0.8)] border border-[rgba(255,255,255,0.08)] rounded-lg hover:bg-[rgba(15,15,20,0.95)] hover:border-primary/30 hover:text-primary transition-all duration-200 text-foreground"
                    >
                      {q}
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
                      className={`max-w-[80%] rounded-lg px-4 py-2.5 ${
                        msg.role === 'user'
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-[rgba(15,15,20,0.8)] text-foreground border border-[rgba(255,255,255,0.08)]'
                      }`}
                      style={{
                        boxShadow: msg.role === 'user' 
                          ? '0 2px 8px rgba(59, 130, 246, 0.2)' 
                          : '0 2px 8px rgba(0, 0, 0, 0.15)'
                      }}
                    >
                      <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                    </div>
                  </div>
                ))}
                {loading && (
                  <div className="flex justify-start">
                    <div className="bg-[rgba(15,15,20,0.8)] border border-[rgba(255,255,255,0.08)] rounded-lg px-4 py-2.5">
                      <Loader2 className="w-4 h-4 animate-spin text-primary" />
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* 输入区域 */}
          <div className="p-4 border-t border-[rgba(255,255,255,0.08)] bg-[rgba(15,15,20,0.5)]">
            <div className="flex gap-2">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="输入您的问题..."
                className="flex-1 px-4 py-2.5 bg-[rgba(15,15,20,0.8)] border border-[rgba(255,255,255,0.08)] rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50 transition-all text-foreground placeholder:text-muted-foreground"
                disabled={loading}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || loading}
                className="px-4 py-2.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed transition-all duration-200 shadow-lg shadow-primary/25 hover:shadow-xl hover:shadow-primary/30"
                aria-label="发送"
              >
                {loading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
