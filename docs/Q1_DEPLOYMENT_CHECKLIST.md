# Q1功能部署检查清单

## ✅ 部署前检查

### 1. 文件完整性 ✅

- [x] `docker-compose.yml` 存在
- [x] `web/backend/Dockerfile` 存在
- [x] `web/frontend/Dockerfile` 存在
- [x] `scripts/init.sql` 存在
- [x] `nginx.conf` 存在
- [x] `migrations/add_chatbot_tables.sql` 存在
- [x] `migrations/add_anomaly_table.sql` 存在
- [x] `cloudlens/core/llm_client.py` 存在
- [x] `cloudlens/core/anomaly_detector.py` 存在
- [x] `cloudlens/core/notification_service.py` 存在
- [x] `cloudlens/core/budget_alert_service.py` 存在
- [x] `web/backend/api/v1/chatbot.py` 存在
- [x] `web/backend/api/v1/anomaly.py` 存在
- [x] `web/frontend/components/ai-chatbot.tsx` 存在

### 2. 代码集成检查 ✅

- [x] `web/backend/api/__init__.py` 中已注册chatbot路由
- [x] `web/backend/api/__init__.py` 中已注册anomaly路由
- [x] `web/frontend/app/layout.tsx` 中已导入AIChatbot组件
- [x] `web/frontend/app/layout.tsx` 中已渲染AIChatbot组件

### 3. 依赖检查 ✅

- [x] `requirements.txt` 中已添加 `anthropic>=0.18.0`
- [x] `requirements.txt` 中已添加 `openai>=1.0.0`
- [x] `requirements.txt` 中已添加 `requests>=2.31.0`

---

## 🚀 部署步骤

### 步骤1: 配置环境变量

```bash
# 复制模板
cp .env.example .env

# 编辑.env，至少配置：
# - ANTHROPIC_API_KEY 或 OPENAI_API_KEY（AI功能必需）
# - 数据库密码等
```

### 步骤2: 启动服务

```bash
# 使用Docker Compose
docker-compose up -d

# 或手动启动
# 后端
cd web/backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000

# 前端（新终端）
cd web/frontend
npm run dev
```

### 步骤3: 初始化数据库

```bash
# 执行数据库迁移
docker-compose exec -T mysql mysql -u cloudlens -pcloudlens123 cloudlens < migrations/init_mysql_schema.sql
docker-compose exec -T mysql mysql -u cloudlens -pcloudlens123 cloudlens < migrations/add_chatbot_tables.sql
docker-compose exec -T mysql mysql -u cloudlens -pcloudlens123 cloudlens < migrations/add_anomaly_table.sql
```

### 步骤4: 重启后端服务（重要！）

**必须重启后端服务才能加载新的API路由**

```bash
# 方式1: Docker Compose
docker-compose restart backend

# 方式2: 手动重启
# 停止当前服务 (Ctrl+C)
# 重新启动
cd web/backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 步骤5: 验证部署

```bash
# 1. 检查后端健康
curl http://localhost:8000/health

# 2. 检查API路由（重启后应该返回200或正确的错误信息）
curl http://localhost:8000/api/v1/chatbot/sessions
curl http://localhost:8000/api/v1/anomaly/list
curl http://localhost:8000/api/v1/budgets

# 3. 检查前端
curl http://localhost:3000

# 4. 打开浏览器访问
# http://localhost:3000
# 查看右下角是否有AI助手图标
```

---

## 🔍 故障排查

### 问题1: API路由返回404

**原因**: 后端服务未重启，新路由未加载

**解决**:
```bash
# 重启后端服务
docker-compose restart backend
# 或手动重启
```

### 问题2: AI Chatbot不显示

**原因1**: 前端服务未重启
```bash
# 清除缓存并重启
cd web/frontend
rm -rf .next
npm run dev
```

**原因2**: 浏览器缓存
- 强制刷新: `Cmd+Shift+R` (Mac) 或 `Ctrl+Shift+R` (Windows)

**原因3**: 组件未正确导入
```bash
# 检查layout.tsx
grep "AIChatbot" web/frontend/app/layout.tsx
# 应该看到:
# import { AIChatbot } from "@/components/ai-chatbot";
# <AIChatbot />
```

### 问题3: AI功能提示"服务不可用"

**原因**: 未配置AI API密钥

**解决**:
```bash
# 在.env文件中添加（至少一个）
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
# 或
OPENAI_API_KEY=sk-xxxxx

# 重启后端服务
docker-compose restart backend
```

### 问题4: 数据库表不存在

**原因**: 未执行数据库迁移

**解决**:
```bash
# 执行迁移脚本
docker-compose exec -T mysql mysql -u cloudlens -pcloudlens123 cloudlens < migrations/add_chatbot_tables.sql
docker-compose exec -T mysql mysql -u cloudlens -pcloudlens123 cloudlens < migrations/add_anomaly_table.sql
```

---

## ✅ 部署验证清单

部署完成后，验证以下功能：

- [ ] 后端健康检查: `curl http://localhost:8000/health` 返回200
- [ ] Chatbot API: `curl http://localhost:8000/api/v1/chatbot/sessions` 返回200或正确错误
- [ ] 异常检测API: `curl http://localhost:8000/api/v1/anomaly/list` 返回200或正确错误
- [ ] 预算API: `curl http://localhost:8000/api/v1/budgets` 返回200或正确错误
- [ ] 前端页面: 访问 http://localhost:3000 正常显示
- [ ] AI Chatbot: 右下角显示蓝色圆形按钮
- [ ] 数据库表: 使用MySQL客户端检查表是否存在

---

## 📝 完成标志

当以下所有项都完成时，Q1功能部署成功：

✅ 所有文件存在  
✅ 服务正常启动  
✅ 数据库迁移完成  
✅ 后端服务已重启  
✅ API路由可访问  
✅ 前端组件显示正常  
✅ 功能可正常使用  

---

**最后更新**: 2026-01-18
