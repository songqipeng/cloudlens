# Q1 功能故障排查指南

## AI Chatbot 不显示问题

### 问题：右下角看不到AI助手图标

#### 可能原因和解决方法

**1. 前端服务未重启**

组件已添加到 `layout.tsx`，但需要重启前端服务才能生效。

```bash
# 停止当前前端服务（Ctrl+C）
# 然后重新启动
cd web/frontend
npm run dev
```

**2. 浏览器缓存**

清除浏览器缓存或强制刷新：
- Mac: `Cmd + Shift + R`
- Windows/Linux: `Ctrl + Shift + R`
- 或打开开发者工具（F12），右键刷新按钮选择"清空缓存并硬性重新加载"

**3. 检查组件是否正确导入**

打开浏览器开发者工具（F12），查看Console是否有错误：

```javascript
// 应该能看到类似这样的日志（如果没有错误）
// 或者检查Network标签，看是否有加载失败的文件
```

**4. 检查文件路径**

确认文件存在：
```bash
ls -la web/frontend/components/ai-chatbot.tsx
```

**5. 检查布局文件**

确认 `web/frontend/app/layout.tsx` 中包含：
```tsx
import { AIChatbot } from "@/components/ai-chatbot";
// ...
<AIChatbot />
```

**6. 手动测试组件**

创建一个测试页面验证组件是否正常工作：

创建 `web/frontend/app/test-chatbot/page.tsx`：
```tsx
"use client"

import { AIChatbot } from "@/components/ai-chatbot";

export default function TestChatbotPage() {
  return (
    <div>
      <h1>AI Chatbot 测试页面</h1>
      <p>如果能看到右下角的蓝色圆形按钮，说明组件正常工作</p>
      <AIChatbot />
    </div>
  );
}
```

然后访问 `http://localhost:3000/test-chatbot` 查看是否显示。

**7. 检查Tailwind CSS配置**

确认 `tailwind.config.js` 或 `postcss.config.mjs` 配置正确，包含组件路径。

**8. 检查z-index冲突**

如果页面有其他元素使用了高z-index，可能会遮挡按钮。检查浏览器开发者工具，查看按钮元素是否存在但被遮挡。

### 快速诊断步骤

1. **检查服务状态**
   ```bash
   # 确认前端服务正在运行
   curl http://localhost:3000
   ```

2. **检查控制台错误**
   - 打开浏览器开发者工具（F12）
   - 查看Console标签是否有错误
   - 查看Network标签是否有404错误

3. **检查元素是否存在**
   - 打开开发者工具
   - 使用元素选择器（Ctrl+Shift+C 或 Cmd+Shift+C）
   - 尝试选择右下角区域
   - 或使用控制台执行：
     ```javascript
     document.querySelector('button[aria-label="打开AI助手"]')
     ```

4. **重启服务**
   ```bash
   # 完全停止并重启
   cd web/frontend
   # 停止服务（Ctrl+C）
   rm -rf .next  # 清除Next.js缓存
   npm run dev
   ```

### 如果仍然不显示

**检查组件代码**

打开浏览器控制台，执行：
```javascript
// 检查React组件是否渲染
console.log(document.querySelector('[aria-label="打开AI助手"]'))
```

**查看网络请求**

检查是否有API调用失败：
- 打开Network标签
- 刷新页面
- 查看是否有 `/api/v1/chatbot` 相关的请求失败

**检查环境变量**

确认 `.env` 文件配置正确（虽然不影响显示，但影响功能）：
```bash
cat .env | grep -i anthropic
cat .env | grep -i openai
```

### 常见错误信息

**错误：`Cannot find module '@/components/ai-chatbot'`**
- 解决：确认文件路径正确，重启服务

**错误：`Module not found: Can't resolve 'lucide-react'`**
- 解决：`cd web/frontend && npm install lucide-react`

**错误：组件渲染但按钮不可见**
- 检查CSS样式，确认 `z-index: 50` 和 `position: fixed` 生效
- 检查是否有其他元素遮挡

---

## 其他常见问题

### 成本异常检测不工作

**检查数据库表**
```bash
docker-compose exec mysql mysql -u cloudlens -p cloudlens -e "SHOW TABLES LIKE 'cost_anomalies';"
```

**检查API端点**
```bash
curl http://localhost:8000/api/v1/anomaly/list
```

### 预算告警不发送

**检查通知配置**
```bash
# 确认.env中有通知配置
cat .env | grep -i smtp
cat .env | grep -i dingtalk
```

**检查日志**
```bash
docker-compose logs backend | grep -i alert
```

---

## 获取帮助

如果以上方法都无法解决问题，请：

1. 收集错误信息：
   - 浏览器控制台错误
   - 后端日志：`docker-compose logs backend`
   - 前端日志：查看终端输出

2. 检查版本：
   ```bash
   node --version
   npm --version
   docker --version
   ```

3. 提交Issue，包含：
   - 操作系统版本
   - Node.js版本
   - 错误日志
   - 复现步骤
