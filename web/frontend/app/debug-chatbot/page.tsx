"use client"

import { AIChatbot } from "@/components/ai-chatbot";
import { useEffect, useState } from "react";

export default function DebugChatbotPage() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    console.log("DebugChatbotPage mounted");
  }, []);

  return (
    <div style={{ padding: '50px', minHeight: '100vh', backgroundColor: '#f5f5f5' }}>
      <h1>AI Chatbot 调试页面</h1>
      <div style={{ marginTop: '20px', padding: '20px', backgroundColor: 'white', borderRadius: '8px' }}>
        <h2>组件状态</h2>
        <p>页面已挂载: {mounted ? '是' : '否'}</p>
        <p>组件已导入: {typeof AIChatbot !== 'undefined' ? '是' : '否'}</p>
        
        <div style={{ marginTop: '30px', padding: '20px', backgroundColor: '#e3f2fd', borderRadius: '8px' }}>
          <h3>说明</h3>
          <p>如果组件正常工作，你应该能看到：</p>
          <ul>
            <li>右下角有一个蓝色圆形按钮（MessageCircle图标）</li>
            <li>按钮位置: fixed bottom-6 right-6</li>
            <li>z-index: 50</li>
          </ul>
        </div>
      </div>
      
      <div style={{ marginTop: '30px' }}>
        <h2>渲染组件</h2>
        <AIChatbot />
      </div>
    </div>
  );
}
