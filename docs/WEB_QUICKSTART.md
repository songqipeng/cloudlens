# CloudLens Web - 快速开始指南

> **版本**: v2.1.0  
> **更新日期**: 2025-12

---

## 📋 目录

1. [环境要求](#环境要求)
2. [安装步骤](#安装步骤)
3. [启动服务](#启动服务)
4. [访问界面](#访问界面)
5. [功能说明](#功能说明)
6. [常见问题](#常见问题)

---

## 🔧 环境要求

### 系统要求

- **操作系统**: macOS, Linux, Windows
- **Python版本**: 3.8+
- **Node.js版本**: 18+
- **npm版本**: 9+

### 依赖检查

```bash
# 检查Python版本
python3 --version  # 应该 >= 3.8

# 检查Node.js版本
node --version  # 应该 >= 18

# 检查npm版本
npm --version  # 应该 >= 9
```

---

## 📦 安装步骤

### 1. 安装后端依赖

```bash
# 进入项目根目录
cd /Users/mac/aliyunidle

# 安装Python依赖
pip install -r requirements.txt

# 安装Web后端依赖
pip install -r web/backend/requirements.txt
```

### 2. 安装前端依赖

```bash
# 进入前端目录
cd web/frontend

# 安装Node.js依赖
npm install
```

---

## 🚀 启动服务

### 方式1: 分别启动（推荐开发）

#### 启动后端服务

```bash
# 在项目根目录
cd web/backend

# 启动FastAPI服务
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

后端服务将在 `http://127.0.0.1:8000` 启动。

#### 启动前端服务

```bash
# 在新终端窗口
cd web/frontend

# 启动Next.js开发服务器
npm run dev
```

前端服务将在 `http://localhost:3000` 启动。

### 方式2: 使用脚本启动（推荐生产）

创建启动脚本 `start_web.sh`:

```bash
#!/bin/bash

# 启动后端
cd web/backend
uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# 等待后端启动
sleep 3

# 启动前端
cd ../frontend
npm run build
npm start &
FRONTEND_PID=$!

echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo "Backend: http://127.0.0.1:8000"
echo "Frontend: http://localhost:3000"

# 等待用户中断
wait
```

---

## 🌐 访问界面

### 1. 打开浏览器

访问: `http://localhost:3000`

### 2. 首次使用

如果还没有配置账号，需要先配置：

**方式1: 通过CLI配置**
```bash
./cl config add \
  --provider aliyun \
  --name prod \
  --region cn-hangzhou \
  --ak YOUR_AK \
  --sk YOUR_SK
```

**方式2: 通过Web界面配置**
- 访问 `http://localhost:3000/settings/accounts`
- 点击"添加账号"
- 填写账号信息

### 3. 开始使用

- **Dashboard**: `http://localhost:3000` - 查看资源概览
- **资源管理**: `http://localhost:3000/resources` - 查看和管理资源
- **成本分析**: `http://localhost:3000/cost` - 查看成本分析
- **安全合规**: `http://localhost:3000/security` - 查看安全检查
- **优化建议**: `http://localhost:3000/optimization` - 查看优化建议
- **报告生成**: `http://localhost:3000/reports` - 生成报告
- **设置**: `http://localhost:3000/settings` - 配置设置

---

## 📖 功能说明

### Dashboard（仪表盘）

- **成本概览**: 总成本、趋势、环比/同比增长
- **资源统计**: 资源总数、各类型资源数量
- **闲置资源**: 闲置资源列表和详情
- **告警信息**: 安全告警、即将到期资源
- **标签覆盖率**: 资源标签完整度

### 资源管理

- **资源列表**: 支持ECS、RDS、Redis、VPC等
- **资源详情**: 查看资源详细信息、监控数据
- **搜索筛选**: 按名称、状态、区域筛选
- **排序**: 按成本、创建时间等排序

### 成本分析

- **成本概览**: 本月、上月成本对比
- **成本趋势**: 30天成本趋势图表
- **成本构成**: 按资源类型、区域分析
- **成本预测**: AI预测未来成本（开发中）

### 安全合规

- **安全评分**: 综合安全评分（0-100）
- **安全检查**: 公网暴露、停止实例、标签检查
- **CIS合规**: CIS Benchmark合规检查（开发中）
- **权限审计**: 权限审计和最小权限建议

### 优化建议

- **优化建议列表**: 基于资源分析的建议
- **节省潜力**: 预估可节省金额
- **优先级排序**: 按重要性排序
- **批量操作**: 批量打标签、批量修复

### 报告生成

- **报告类型**: 综合报告、资源清单、成本分析、安全报告
- **输出格式**: Excel、HTML、PDF
- **报告历史**: 查看历史生成的报告

---

## ❓ 常见问题

### Q1: 后端服务启动失败

**问题**: `ModuleNotFoundError: No module named 'fastapi'`

**解决**:
```bash
pip install -r web/backend/requirements.txt
```

### Q2: 前端服务启动失败

**问题**: `Error: Cannot find module`

**解决**:
```bash
cd web/frontend
rm -rf node_modules package-lock.json
npm install
```

### Q3: API请求失败

**问题**: `Failed to fetch` 或 `CORS error`

**解决**:
1. 确保后端服务正在运行（`http://127.0.0.1:8000`）
2. 检查后端CORS配置（`web/backend/main.py`）
3. 检查浏览器控制台错误信息

### Q4: 账号配置后无法查询资源

**问题**: 显示"No accounts configured"

**解决**:
1. 检查账号配置是否正确
2. 检查AccessKey是否有权限
3. 查看后端日志错误信息

### Q5: 页面加载缓慢

**问题**: 首次加载很慢

**解决**:
1. 检查网络连接
2. 检查后端API响应时间
3. 使用缓存功能（默认启用）

---

## 🔍 调试技巧

### 查看后端日志

后端服务会输出详细的日志信息，包括：
- API请求日志
- 错误信息
- 执行时间

### 查看前端日志

打开浏览器开发者工具（F12）：
- **Console**: 查看JavaScript错误
- **Network**: 查看API请求和响应
- **Application**: 查看本地存储

### 测试API

使用curl测试API：

```bash
# 测试健康检查
curl http://127.0.0.1:8000/health

# 测试Dashboard摘要
curl http://127.0.0.1:8000/api/dashboard/summary

# 测试资源列表
curl "http://127.0.0.1:8000/api/resources?type=ecs&page=1&pageSize=20"
```

---

## 📚 相关文档

- [产品设计文档](WEB_PRODUCT_DESIGN.md)
- [实施计划](WEB_IMPLEMENTATION_PLAN.md)
- [开发计划](WEB_DEVELOPMENT_PLAN.md)
- [用户指南](../USER_GUIDE.md)

---

## 🆘 获取帮助

- **GitHub Issues**: 提交Bug或功能请求
- **文档**: 查看完整文档
- **CLI帮助**: `./cl --help`

---

**最后更新**: 2025-12





