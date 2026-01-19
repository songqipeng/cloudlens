"use client"

import { AIChatbot } from "@/components/ai-chatbot";

export default function TestChatbotPage() {
  return (
    <div style={{ padding: '50px', minHeight: '100vh' }}>
      <h1 style={{ marginBottom: '20px' }}>AI Chatbot 测试页面</h1>
      <p style={{ marginBottom: '20px' }}>
        如果能看到右下角的蓝色圆形按钮，说明组件正常工作。
      </p>
      <p style={{ color: '#666' }}>
        按钮应该在页面右下角，是一个蓝色圆形图标。
      </p>
      <AIChatbot />
    </div>
  );
}
