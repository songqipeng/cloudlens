# CloudLens 本地测试指南

> **版本**: 1.0  
> **更新日期**: 2026-01-18  
> **适用场景**: 本地开发、功能测试、问题排查

---

## 📋 目录

1. [环境准备](#环境准备)
2. [快速启动](#快速启动)
3. [功能测试](#功能测试)
4. [问题排查](#问题排查)
5. [开发调试](#开发调试)

---

## 🔧 环境准备

### 必需软件

- **Docker & Docker Compose** (推荐方式)
  ```bash
  docker --version  # 应该 >= 20.10
  docker-compose --version  # 应该 >= 1.29
  ```

- **Python 3.11+** (如果不用Docker)
  ```bash
  python3 --version  # 应该 >= 3.11
  ```

- **Node.js 20+** (如果不用Docker)
  ```bash
  node --version  # 应该 >= 20
  npm --version  # 应该 >= 9
  ```

- **MySQL 8.0+** (可选，Docker会自动启动)
  ```bash
  mysql --version  # 应该 >= 8.0
  ```

### 克隆项目

```bash
git clone https://github.com/songqipeng/cloudlens.git
cd cloudlens
```

---

## 🚀 快速启动

### 方式一：Docker Compose（推荐，最简单）

#### 1. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，至少配置AI服务密钥
nano .env
```

**必需配置**（至少一个）:
```bash
# 使用Claude（推荐）
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
LLM_PROVIDER=claude

# 或使用OpenAI
OPENAI_API_KEY=sk-xxxxx
LLM_PROVIDER=openai
```

**可选配置**:
```bash
# 数据库配置（默认值通常可用）
MYSQL_ROOT_PASSWORD=cloudlens_root_2024
MYSQL_USER=cloudlens
MYSQL_PASSWORD=cloudlens123
MYSQL_DATABASE=cloudlens

# 通知服务配置（可选）
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your_email@example.com
SMTP_PASSWORD=your_password
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=xxx
WECHAT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
```

#### 2. 配置云账号（如需要测试云资源功能）

```bash
# 创建配置目录
mkdir -p config

# 复制配置模板
cp config/config.json.example config/config.json

# 编辑配置文件
nano config/config.json
```

**配置示例**:
```json
{
  "accounts": [
    {
      "name": "test_account",
      "alias": "测试账号",
      "provider": "aliyun",
      "region": "cn-hangzhou",
      "access_key_id": "your_access_key_id",
      "access_key_secret": "your_access_key_secret"
    }
  ]
}
```

#### 3. 启动所有服务

```bash
# 启动所有服务（MySQL, Redis, Backend, Frontend, Nginx）
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

#### 4. 初始化数据库（首次运行）

```bash
# 等待MySQL完全启动（约10-15秒）
sleep 15

# 执行数据库迁移
docker-compose exec -T mysql mysql -u cloudlens -pcloudlens123 cloudlens < migrations/init_mysql_schema.sql
docker-compose exec -T mysql mysql -u cloudlens -pcloudlens123 cloudlens < migrations/add_chatbot_tables.sql
docker-compose exec -T mysql mysql -u cloudlens -pcloudlens123 cloudlens < migrations/add_anomaly_table.sql

# 验证数据库表
docker-compose exec mysql mysql -u cloudlens -pcloudlens123 cloudlens -e "SHOW TABLES;"
```

#### 5. 验证服务

```bash
# 检查后端健康
curl http://localhost:8000/health
# 应该返回: {"status":"healthy","timestamp":"...","service":"cloudlens-api","version":"1.1.0"}

# 检查前端
curl -I http://localhost:3000
# 应该返回: HTTP/1.1 200 OK

# 检查API文档
curl -I http://localhost:8000/docs
# 应该返回: HTTP/1.1 200 OK
```

#### 6. 访问应用

- **前端界面**: http://localhost:3000
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **Nginx Gateway**: http://localhost:80

---

### 方式二：本地开发环境（用于开发和调试）

#### 1. 安装依赖

```bash
# 安装Python依赖
pip install -r requirements.txt

# 安装前端依赖
cd web/frontend
npm install
cd ../..
```

#### 2. 启动MySQL（如果使用MySQL）

**选项A: 使用Docker启动MySQL**
```bash
docker run -d \
  --name cloudlens-mysql \
  -e MYSQL_ROOT_PASSWORD=cloudlens_root_2024 \
  -e MYSQL_DATABASE=cloudlens \
  -e MYSQL_USER=cloudlens \
  -e MYSQL_PASSWORD=cloudlens123 \
  -p 3306:3306 \
  mysql:8.0

# 等待MySQL启动
sleep 10

# 初始化数据库
mysql -u cloudlens -pcloudlens123 cloudlens < migrations/init_mysql_schema.sql
mysql -u cloudlens -pcloudlens123 cloudlens < migrations/add_chatbot_tables.sql
mysql -u cloudlens -pcloudlens123 cloudlens < migrations/add_anomaly_table.sql
```

**选项B: 使用本地MySQL**
```bash
# macOS
brew services start mysql

# 创建数据库和用户
mysql -u root -p <<EOF
CREATE DATABASE cloudlens CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'cloudlens'@'localhost' IDENTIFIED BY 'cloudlens123';
GRANT ALL PRIVILEGES ON cloudlens.* TO 'cloudlens'@'localhost';
FLUSH PRIVILEGES;
EOF

# 初始化数据库
mysql -u cloudlens -pcloudlens123 cloudlens < migrations/init_mysql_schema.sql
mysql -u cloudlens -pcloudlens123 cloudlens < migrations/add_chatbot_tables.sql
mysql -u cloudlens -pcloudlens123 cloudlens < migrations/add_anomaly_table.sql
```

#### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件
nano .env
```

**必需配置**:
```bash
# 数据库配置
DB_TYPE=mysql
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=cloudlens
MYSQL_PASSWORD=cloudlens123
MYSQL_DATABASE=cloudlens

# AI服务配置（至少一个）
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
# 或
OPENAI_API_KEY=sk-xxxxx
LLM_PROVIDER=claude  # 或 openai
```

#### 4. 启动服务

**终端1 - 启动后端**:
```bash
cd web/backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**终端2 - 启动前端**:
```bash
cd web/frontend
npm run dev
```

#### 5. 访问应用

- **前端界面**: http://localhost:3000
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs

---

## 🧪 功能测试

### 1. 测试AI Chatbot

#### 测试步骤

1. **打开浏览器**: 访问 http://localhost:3000
2. **查找AI助手**: 
   - 在页面右下角应该看到**蓝色圆形按钮**（MessageCircle图标）
   - 如果看不到，请：
     - 强制刷新浏览器: `Cmd+Shift+R` (Mac) 或 `Ctrl+Shift+R` (Windows)
     - 检查浏览器控制台是否有错误（F12）
     - 重启前端服务: `cd web/frontend && rm -rf .next && npm run dev`
3. **测试对话**:
   - 点击按钮打开聊天窗口
   - 输入问题："为什么这个月成本提升了10%？"
   - 查看AI回复
4. **测试功能**:
   - ✅ 快速问题按钮（点击预设问题）
   - ✅ 最小化/展开功能
   - ✅ 关闭功能
   - ✅ 消息发送和接收
   - ✅ 对话历史（刷新页面后应该保留）

#### 预期结果

- AI助手按钮在右下角可见
- 点击后聊天窗口正常打开
- 可以发送消息并收到AI回复
- UI符合深色主题风格（glass效果）

#### 常见问题

- **按钮不显示**: 清除浏览器缓存，重启前端服务
- **API错误**: 检查`.env`中是否配置了AI API密钥
- **超时**: 检查网络连接，AI API可能需要较长时间响应

---

### 2. 测试折扣分析列表页

#### 测试步骤

1. **访问页面**: 
   ```
   http://localhost:3000/a/[账号名]/discounts
   ```
   或通过导航菜单进入"折扣分析"

2. **测试排序功能**:
   - 点击"产品"列头 → 应该按产品名称排序
   - 点击"原价"列头 → 应该按金额排序
   - 点击"节省"列头 → 应该按折扣金额排序
   - 再次点击 → 应该切换升序/降序
   - 验证排序图标正确显示（↑ 升序，↓ 降序）

3. **测试筛选功能**:
   - 点击"全部"按钮 → 显示所有数据
   - 点击"包年包月"按钮 → 只显示Subscription类型
   - 点击"按量付费"按钮 → 只显示PayAsYouGo类型
   - 验证筛选后表格数据正确更新
   - 验证筛选后汇总卡片显示"（仅当前筛选）"

4. **测试搜索功能**:
   - 在搜索框输入产品代码（如"ecs"）
   - 验证表格正确过滤
   - 输入产品名称（如"云服务器"）
   - 验证搜索结果正确
   - 清空搜索 → 恢复显示所有数据

5. **测试数据准确性**:
   - 随机选择几行数据
   - 手动计算：`折扣金额 = 原价 - 折后价`
   - 验证显示值与计算值一致
   - 验证实付比例 = 折后价 / 原价
   - 验证折扣（折） = 实付比例 × 10

6. **测试边界情况**:
   - 切换到无数据的账期 → 应该显示友好提示
   - 查看免费项目 → 应该显示"免费"
   - 查看null值 → 应该显示"-"

#### 预期结果

- 所有功能正常工作
- 数据计算准确
- UI响应流畅
- 错误处理友好

---

### 3. 测试成本异常检测

#### 测试步骤

1. **调用检测API**:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/anomaly/detect?account=your_account"
   ```

2. **查看检测结果**:
   ```bash
   curl "http://localhost:8000/api/v1/anomaly/list?account=your_account"
   ```

3. **验证数据**:
   - 检查返回的异常记录
   - 验证异常严重程度（low/medium/high/critical）
   - 验证AI根因分析是否存在
   - 验证优化建议是否存在

#### 预期结果

- API正常响应
- 返回JSON格式数据
- 异常记录包含完整信息

---

### 4. 测试预算管理

#### 测试步骤

1. **创建预算**:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/budgets" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "测试预算",
       "amount": 5000.00,
       "period": "monthly",
       "type": "total",
       "start_date": "2026-01-01T00:00:00Z",
       "account_id": "your_account",
       "alerts": [
         {
           "percentage": 80.0,
           "enabled": true,
           "notification_channels": ["email"]
         }
       ]
     }'
   ```

2. **查看预算列表**:
   ```bash
   curl "http://localhost:8000/api/v1/budgets"
   ```

3. **查看预算状态**:
   ```bash
   curl "http://localhost:8000/api/v1/budgets/{budget_id}/status"
   ```

4. **测试告警检查**:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/budgets/check-alerts"
   ```

#### 预期结果

- 预算创建成功
- 预算状态计算正确
- 告警机制正常工作

---

## 🔍 问题排查

### 问题1: 服务无法启动

**症状**: `docker-compose up -d` 失败

**排查步骤**:
```bash
# 1. 检查Docker是否运行
docker ps

# 2. 查看详细错误
docker-compose up

# 3. 检查端口占用
lsof -i :3000  # 前端端口
lsof -i :8000  # 后端端口
lsof -i :3306  # MySQL端口
lsof -i :6379  # Redis端口
lsof -i :80    # Nginx端口

# 4. 清理旧容器
docker-compose down
docker-compose up -d
```

### 问题2: 数据库连接失败

**症状**: 后端日志显示数据库连接错误

**排查步骤**:
```bash
# 1. 检查MySQL是否运行
docker-compose ps mysql
# 或
brew services list | grep mysql

# 2. 测试数据库连接
mysql -u cloudlens -pcloudlens123 -h localhost cloudlens -e "SELECT 1;"

# 3. 检查数据库表
mysql -u cloudlens -pcloudlens123 cloudlens -e "SHOW TABLES;"

# 4. 查看MySQL日志
docker-compose logs mysql
```

### 问题3: 前端页面空白或错误

**症状**: 浏览器显示空白页面或错误

**排查步骤**:
```bash
# 1. 检查前端服务
curl http://localhost:3000

# 2. 查看前端日志
docker-compose logs frontend
# 或（本地启动）
cd web/frontend && npm run dev

# 3. 检查浏览器控制台
# 打开浏览器开发者工具（F12），查看Console标签

# 4. 清除缓存并重启
cd web/frontend
rm -rf .next
npm run dev
```

### 问题4: API返回404

**症状**: API调用返回404错误

**排查步骤**:
```bash
# 1. 检查后端服务
curl http://localhost:8000/health

# 2. 查看后端日志
docker-compose logs backend
# 或（本地启动）
# 查看uvicorn输出

# 3. 检查API路由
curl http://localhost:8000/docs
# 在API文档中查看可用端点

# 4. 重启后端服务
docker-compose restart backend
# 或（本地启动）
# 停止并重新启动uvicorn
```

### 问题5: AI Chatbot不显示

**排查步骤**:
```bash
# 1. 检查组件文件
ls -la web/frontend/components/ai-chatbot.tsx

# 2. 检查Layout集成
grep "AIChatbot" web/frontend/app/layout.tsx

# 3. 清除缓存并重启前端
cd web/frontend
rm -rf .next
npm run dev

# 4. 检查浏览器控制台
# 打开F12，查看Console是否有错误

# 5. 访问调试页面
# http://localhost:3000/debug-chatbot
```

---

## 🛠️ 开发调试

### 查看日志

```bash
# Docker方式 - 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f mysql

# 本地方式 - 后端日志在终端输出
# 前端日志在终端输出
```

### 调试后端

```bash
# 使用Python调试器
cd web/backend
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 在代码中添加断点
import pdb; pdb.set_trace()
```

### 调试前端

```bash
# 启动开发服务器（自动热重载）
cd web/frontend
npm run dev

# 使用浏览器开发者工具
# F12 → Console标签查看日志
# F12 → Network标签查看API请求
# F12 → Elements标签检查DOM
```

### 测试API

```bash
# 使用curl测试
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/chatbot/sessions

# 使用API文档测试
# 访问 http://localhost:8000/docs
# 在Swagger UI中直接测试API
```

### 数据库操作

```bash
# 连接数据库
docker-compose exec mysql mysql -u cloudlens -pcloudlens123 cloudlens

# 或本地MySQL
mysql -u cloudlens -pcloudlens123 cloudlens

# 常用SQL命令
SHOW TABLES;
SELECT * FROM chat_sessions LIMIT 10;
SELECT * FROM cost_anomalies LIMIT 10;
SELECT * FROM budgets LIMIT 10;
```

---

## 📝 测试检查清单

### 基础功能
- [ ] 服务正常启动
- [ ] 数据库连接正常
- [ ] 前端页面正常加载
- [ ] 后端API正常响应

### AI Chatbot
- [ ] 按钮在右下角可见
- [ ] 聊天窗口正常打开
- [ ] 可以发送消息
- [ ] AI回复正常
- [ ] UI符合设计规范

### 折扣分析
- [ ] 页面正常加载
- [ ] 数据正确显示
- [ ] 排序功能正常
- [ ] 筛选功能正常
- [ ] 搜索功能正常
- [ ] 数据计算准确

### 成本异常检测
- [ ] API正常响应
- [ ] 检测功能正常
- [ ] 异常记录正确

### 预算管理
- [ ] 创建预算正常
- [ ] 预算状态正确
- [ ] 告警机制正常

---

## 🎯 快速测试命令

```bash
# 一键测试脚本
cd /Users/songqipeng/cloudlens
python3 scripts/test_q1_features.py

# 或手动测试
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/chatbot/sessions
curl http://localhost:3000
```

---

**最后更新**: 2026-01-18  
**维护者**: CloudLens Team
