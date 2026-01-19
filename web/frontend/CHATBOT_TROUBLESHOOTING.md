# AI Chatbot 不显示 - 快速排查

## 立即尝试的解决方法

### 方法1: 重启前端服务（最常见）

```bash
# 1. 停止当前前端服务（在运行npm run dev的终端按 Ctrl+C）

# 2. 清除Next.js缓存
cd web/frontend
rm -rf .next

# 3. 重新启动
npm run dev
```

### 方法2: 清除浏览器缓存

1. 打开浏览器开发者工具（F12 或 Cmd+Option+I）
2. 右键点击刷新按钮
3. 选择"清空缓存并硬性重新加载"

或使用快捷键：
- Mac: `Cmd + Shift + R`
- Windows: `Ctrl + Shift + F5`

### 方法3: 检查控制台错误

1. 打开浏览器开发者工具（F12）
2. 查看 Console 标签
3. 如果有红色错误，请截图保存

### 方法4: 手动检查组件

在浏览器控制台执行：

```javascript
// 检查按钮是否存在
document.querySelector('button[aria-label="打开AI助手"]')

// 如果返回 null，说明组件没有渲染
// 如果有返回，说明按钮存在但可能被遮挡
```

### 方法5: 检查文件路径

确认文件存在：
```bash
ls -la web/frontend/components/ai-chatbot.tsx
```

如果文件不存在，需要重新创建。

## 如果仍然不显示

请检查：

1. **前端服务是否正常运行**
   - 访问 http://localhost:3000 是否正常
   - 查看终端是否有错误信息

2. **组件导入是否正确**
   - 打开 `web/frontend/app/layout.tsx`
   - 确认有 `import { AIChatbot } from "@/components/ai-chatbot";`
   - 确认有 `<AIChatbot />`

3. **检查TypeScript编译错误**
   ```bash
   cd web/frontend
   npm run build
   ```
   查看是否有编译错误

4. **检查依赖是否安装**
   ```bash
   cd web/frontend
   npm install
   ```

## 临时测试方法

创建一个测试页面验证组件：

1. 创建文件 `web/frontend/app/test/page.tsx`：
```tsx
"use client"

import { AIChatbot } from "@/components/ai-chatbot";

export default function TestPage() {
  return (
    <div style={{ padding: '50px' }}>
      <h1>AI Chatbot 测试</h1>
      <p>如果能看到右下角的蓝色圆形按钮，说明组件正常</p>
      <AIChatbot />
    </div>
  );
}
```

2. 访问 http://localhost:3000/test

3. 查看是否显示按钮
