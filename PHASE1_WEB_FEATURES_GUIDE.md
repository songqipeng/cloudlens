# Phase 1 Web 功能查看指南

## 🚀 启动 Web 服务

### 方式 1: 使用启动脚本（推荐）

```bash
cd /Users/mac/cloudlens
bash start_web.sh
```

### 方式 2: 分别启动前后端

#### 启动后端（终端 1）
```bash
cd /Users/mac/cloudlens/web/backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

#### 启动前端（终端 2）
```bash
cd /Users/mac/cloudlens/web/frontend
npm run dev
```

## 🌐 访问界面

1. 打开浏览器访问：`http://localhost:3000`
2. 登录或选择账户
3. 导航到 **Resources（资源）** 页面

## 📍 新增功能位置

### 1. 资源类型按钮

在资源列表页面顶部，您会看到新增的资源类型按钮：
- **MongoDB** - 查询 MongoDB 实例
- **ACK** - 查询 Kubernetes 集群

### 2. 筛选功能

在搜索框右侧，有一个 **"筛选"** 按钮（带筛选图标）：

1. 点击 **"筛选"** 按钮
2. 会展开筛选面板，包含：
   - **状态筛选**：选择资源状态（运行中、已停止等）
   - **区域筛选**：选择资源所在区域
   - **清除筛选**：清除所有筛选条件

### 3. 导出功能

在筛选按钮右侧，有两个导出按钮：
- **CSV** 按钮 - 导出为 CSV 格式
- **Excel** 按钮 - 导出为 Excel 格式

**使用方式**：
1. 可以先用筛选功能筛选出需要的资源
2. 点击 CSV 或 Excel 按钮
3. 浏览器会自动下载文件

### 4. 增强的搜索功能

搜索框现在支持搜索：
- 资源名称
- 资源 ID
- 区域名称

## 🖼️ 界面截图说明

```
┌─────────────────────────────────────────────────────────┐
│  Resources（资源列表）                                    │
├─────────────────────────────────────────────────────────┤
│  [ECS] [RDS] [Redis] ... [MongoDB] [ACK]  ← 新增类型    │
├─────────────────────────────────────────────────────────┤
│  [搜索框] [筛选] [CSV] [Excel]  ← 新增功能              │
│  ┌─────────────────────────────────────┐                │
│  │ 状态: [下拉选择]  区域: [下拉选择]  │  ← 筛选面板     │
│  │        [清除筛选]                    │                │
│  └─────────────────────────────────────┘                │
├─────────────────────────────────────────────────────────┤
│  资源列表表格...                                         │
└─────────────────────────────────────────────────────────┘
```

## 🔍 功能验证清单

- [ ] 能看到 MongoDB 和 ACK 资源类型按钮
- [ ] 点击"筛选"按钮能展开筛选面板
- [ ] 状态筛选下拉框能正常选择
- [ ] 区域筛选下拉框能正常选择
- [ ] 点击 CSV 按钮能下载 CSV 文件
- [ ] 点击 Excel 按钮能下载 Excel 文件
- [ ] 搜索框能搜索资源名称、ID 和区域

## ⚠️ 如果看不到功能

### 1. 检查前端是否重新编译

如果前端服务已经在运行，需要重启：

```bash
# 停止前端服务（Ctrl+C）
# 然后重新启动
cd web/frontend
npm run dev
```

### 2. 清除浏览器缓存

- Chrome/Edge: `Ctrl+Shift+R` (Windows) 或 `Cmd+Shift+R` (Mac)
- Firefox: `Ctrl+F5` (Windows) 或 `Cmd+Shift+R` (Mac)

### 3. 检查浏览器控制台

打开浏览器开发者工具（F12），查看 Console 是否有错误。

### 4. 检查依赖是否安装

```bash
cd web/frontend
npm install
```

确保 `lucide-react` 已安装（用于图标）：
```bash
npm list lucide-react
```

## 📝 后端功能（API）

后端新增的 API 端点可以通过以下方式测试：

### 1. 导出 API

```bash
# 测试 CSV 导出
curl "http://localhost:8000/api/resources/export?type=ecs&format=csv&account=your_account" -o resources.csv

# 测试 Excel 导出
curl "http://localhost:8000/api/resources/export?type=ecs&format=excel&account=your_account" -o resources.xlsx
```

### 2. 监控指标 API

```bash
# 获取资源监控指标
curl "http://localhost:8000/api/resources/i-xxx/metrics?resource_type=ecs&days=7&account=your_account"
```

## 🐛 常见问题

### Q: 导出按钮点击没反应？

A: 检查：
1. 是否有资源数据（按钮在无数据时会被禁用）
2. 浏览器是否阻止了弹窗（需要允许弹窗）
3. 后端服务是否正常运行

### Q: 筛选面板不显示？

A: 检查：
1. 是否点击了"筛选"按钮
2. 浏览器控制台是否有 JavaScript 错误
3. `lucide-react` 图标库是否正常加载

### Q: MongoDB/ACK 按钮点击后没有数据？

A: 这是正常的，如果您的账户中没有这些资源类型，就不会有数据。功能本身是正常的。

## 📞 需要帮助？

如果仍然看不到功能，请：
1. 检查浏览器控制台的错误信息
2. 确认前端服务正常运行
3. 尝试硬刷新浏览器（清除缓存）

