# Q1 功能使用指南

> 本文档详细介绍Q1开发的所有功能如何使用

## 📋 目录

1. [快速开始](#快速开始)
2. [AI Chatbot 使用指南](#ai-chatbot-使用指南)
3. [成本异常检测使用指南](#成本异常检测使用指南)
4. [预算管理使用指南](#预算管理使用指南)
5. [Docker部署使用指南](#docker部署使用指南)
6. [常见问题](#常见问题)

---

## 快速开始

### 前置条件

1. **安装Docker和Docker Compose**
   ```bash
   # 检查Docker是否安装
   docker --version
   docker-compose --version
   ```

2. **配置环境变量**
   ```bash
   # 复制模板
   cp .env.example .env
   
   # 编辑.env文件，至少配置以下内容：
   # - ANTHROPIC_API_KEY 或 OPENAI_API_KEY（AI功能必需）
   # - 数据库密码等
   ```

3. **准备云账号配置**
   ```bash
   # 复制配置模板
   cp config/config.json.example config/config.json
   
   # 编辑config.json，填入你的阿里云/腾讯云AK/SK
   ```

---

## AI Chatbot 使用指南

### 功能概述

AI Chatbot是一个智能助手，可以帮你：
- 分析成本变化原因
- 识别闲置资源
- 提供优化建议
- 解释账单明细
- 预测未来成本

### 使用步骤

#### 1. 启动服务

```bash
# 确保服务已启动
docker-compose up -d

# 检查服务状态
docker-compose ps
```

#### 2. 配置AI服务

在 `.env` 文件中配置AI服务密钥（二选一）：

```bash
# 使用Claude（推荐）
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
LLM_PROVIDER=claude

# 或使用OpenAI
OPENAI_API_KEY=sk-xxxxx
LLM_PROVIDER=openai
```

#### 3. 访问Web界面

1. 打开浏览器访问：`http://localhost:3000`
2. 点击右下角的 **AI助手图标**（蓝色圆形按钮）
3. 聊天窗口会弹出

#### 4. 开始对话

**快速问题示例**：
- "为什么这个月成本提升了10%？"
- "有哪些闲置资源可以优化？"
- "帮我分析一下最近的成本趋势"
- "预测下个月的成本"

**自定义问题**：
- 在输入框输入你的问题
- 按 `Enter` 或点击发送按钮
- AI会自动分析你的成本数据并回答

#### 5. 查看对话历史

- 对话会自动保存到数据库
- 下次打开会显示历史记录
- 可以创建新会话或继续旧会话

### API使用示例

#### 发送聊天消息

```bash
curl -X POST http://localhost:8000/api/v1/chatbot/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "为什么这个月成本提升了10%？"}
    ],
    "account": "your_account_name"
  }'
```

#### 获取会话列表

```bash
curl http://localhost:8000/api/v1/chatbot/sessions?account=your_account_name
```

#### 获取会话消息

```bash
curl http://localhost:8000/api/v1/chatbot/sessions/{session_id}/messages
```

### 注意事项

- ⚠️ **首次使用需要配置AI API密钥**，否则会提示"AI服务不可用"
- 💡 AI会自动获取你当前账号的成本数据作为上下文
- 📝 对话历史会持久化保存，方便后续查看

---

## 成本异常检测使用指南

### 功能概述

成本异常检测可以：
- 自动检测成本异常波动
- 分析异常根因
- 发送告警通知（邮件/钉钉/企业微信）

### 使用步骤

#### 1. 配置告警渠道（可选）

在 `.env` 文件中配置：

```bash
# 邮件告警
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your_email@example.com
SMTP_PASSWORD=your_password
SMTP_FROM=noreply@cloudlens.com

# 钉钉机器人
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=xxx

# 企业微信
WECHAT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
```

#### 2. 手动触发检测

**通过API**：
```bash
curl -X POST "http://localhost:8000/api/v1/anomaly/detect?account=your_account" \
  -H "Content-Type: application/json"
```

**参数说明**：
- `account`: 账号名称（可选，不填则使用默认账号）
- `date`: 检测日期，格式：YYYY-MM-DD（可选，默认今天）
- `baseline_days`: 基线天数，默认30天
- `threshold_std`: 阈值（标准差的倍数），默认2.0

#### 3. 查看异常记录

```bash
curl "http://localhost:8000/api/v1/anomaly/list?account=your_account&severity=high"
```

**参数说明**：
- `account`: 账号名称
- `start_date`: 开始日期（可选）
- `end_date`: 结束日期（可选）
- `severity`: 严重程度（low/medium/high/critical）
- `limit`: 返回数量限制

#### 4. 设置定时检测（推荐）

创建定时任务脚本 `scripts/check_anomalies.py`：

```python
#!/usr/bin/env python3
"""定时检测成本异常"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cloudlens.core.anomaly_detector import AnomalyDetector
from cloudlens.core.notification_service import NotificationService
from cloudlens.core.config import ConfigManager

def main():
    detector = AnomalyDetector()
    notification = NotificationService()
    config = ConfigManager()
    
    # 获取所有账号
    accounts = config.list_accounts()
    
    for account in accounts:
        account_config = config.get_account(account)
        account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        # 检测异常
        anomalies = detector.detect(account_id)
        
        # 发送告警
        for anomaly in anomalies:
            if anomaly.severity in ["high", "critical"]:
                notification.send_anomaly_alert({
                    "account_id": anomaly.account_id,
                    "date": anomaly.date,
                    "current_cost": anomaly.current_cost,
                    "baseline_cost": anomaly.baseline_cost,
                    "deviation_pct": anomaly.deviation_pct,
                    "severity": anomaly.severity,
                    "root_cause": anomaly.root_cause
                })

if __name__ == "__main__":
    main()
```

使用cron定时执行：
```bash
# 每天上午9点检测
0 9 * * * cd /path/to/cloudlens && python scripts/check_anomalies.py
```

### 异常严重程度说明

- **low**: 偏差30-50%
- **medium**: 偏差50-100%
- **high**: 偏差100-200%
- **critical**: 偏差>200%

### 注意事项

- 📊 **需要至少7天的历史数据**才能建立基线
- ⏰ 建议每天定时检测一次
- 🔔 只有high和critical级别的异常会自动发送告警

---

## 预算管理使用指南

### 功能概述

预算管理可以：
- 创建和管理预算
- 实时监控预算执行情况
- 智能预测月底支出
- 自动告警预算超支

### 使用步骤

#### 1. 创建预算

**通过Web界面**：
1. 访问 `http://localhost:3000/budgets`
2. 点击"创建预算"
3. 填写预算信息：
   - 预算名称
   - 预算金额
   - 预算周期（月度/季度/年度）
   - 告警阈值（如80%、100%）

**通过API**：
```bash
curl -X POST http://localhost:8000/api/v1/budgets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "生产环境月度预算",
    "amount": 10000,
    "period": "monthly",
    "type": "total",
    "start_date": "2026-01-01T00:00:00",
    "alerts": [
      {"percentage": 80, "enabled": true, "notification_channels": ["email"]},
      {"percentage": 100, "enabled": true, "notification_channels": ["email", "dingtalk"]}
    ],
    "account": "your_account"
  }'
```

#### 2. 查看预算状态

```bash
curl "http://localhost:8000/api/v1/budgets/{budget_id}/status"
```

返回信息包括：
- 已支出金额
- 剩余预算
- 使用率
- 预测月底支出
- 预测超支金额

#### 3. 查看预算趋势

```bash
curl "http://localhost:8000/api/v1/budgets/{budget_id}/trend?days=30"
```

#### 4. 手动检查告警

```bash
curl -X POST "http://localhost:8000/api/v1/budgets/check-alerts?account=your_account"
```

#### 5. 设置定时检查（推荐）

创建定时任务脚本 `scripts/check_budgets.py`：

```python
#!/usr/bin/env python3
"""定时检查预算告警"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cloudlens.core.budget_alert_service import BudgetAlertService

def main():
    service = BudgetAlertService()
    service.check_all_budgets()

if __name__ == "__main__":
    main()
```

使用cron定时执行：
```bash
# 每天上午10点检查
0 10 * * * cd /path/to/cloudlens && python scripts/check_budgets.py
```

### 预算类型说明

- **total**: 总预算（所有服务）
- **tag**: 按标签预算（如按项目、部门）
- **service**: 按服务预算（如ECS、RDS）

### 告警阈值说明

- **80%**: 预算使用率达到80%时提醒
- **100%**: 预算超支时紧急通知

### 注意事项

- 📅 **预算周期**：月度预算从每月1号开始
- 🔔 **告警去重**：同一天同一阈值只发送一次告警
- 📊 **预测精度**：基于历史数据，误差约15%

---

## Docker部署使用指南

### 完整部署流程

#### 1. 准备环境

```bash
# 克隆代码（如果还没有）
git clone <your-repo-url>
cd cloudlens

# 复制配置文件
cp .env.example .env
cp config/config.json.example config/config.json
```

#### 2. 配置环境变量

编辑 `.env` 文件，至少配置：
```bash
# 数据库密码
MYSQL_PASSWORD=your_secure_password

# AI服务（至少一个）
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
# 或
OPENAI_API_KEY=sk-xxxxx

# 告警通知（可选）
SMTP_HOST=smtp.example.com
SMTP_USER=your_email@example.com
SMTP_PASSWORD=your_password
```

#### 3. 配置云账号

编辑 `config/config.json`：
```json
{
  "default_tenant": "prod",
  "tenants": {
    "prod": {
      "access_key_id": "YOUR_ALIYUN_AK",
      "access_key_secret": "YOUR_ALIYUN_SK",
      "display_name": "生产环境"
    }
  }
}
```

#### 4. 启动服务

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f backend
docker-compose logs -f frontend
```

#### 5. 初始化数据库

```bash
# 执行数据库迁移
docker-compose exec mysql mysql -u cloudlens -p cloudlens < migrations/init_mysql_schema.sql
docker-compose exec mysql mysql -u cloudlens -p cloudlens < migrations/add_chatbot_tables.sql
docker-compose exec mysql mysql -u cloudlens -p cloudlens < migrations/add_anomaly_table.sql
```

或者使用密码：
```bash
docker-compose exec -T mysql mysql -u cloudlens -pcloudlens123 cloudlens < migrations/init_mysql_schema.sql
docker-compose exec -T mysql mysql -u cloudlens -pcloudlens123 cloudlens < migrations/add_chatbot_tables.sql
docker-compose exec -T mysql mysql -u cloudlens -pcloudlens123 cloudlens < migrations/add_anomaly_table.sql
```

#### 6. 访问应用

- **前端**: http://localhost:3000
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **Nginx Gateway**: http://localhost:80

### 常用命令

```bash
# 停止所有服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f [service_name]

# 进入容器
docker-compose exec backend bash
docker-compose exec mysql mysql -u cloudlens -p cloudlens

# 重建镜像
docker-compose build --no-cache

# 清理数据（谨慎使用）
docker-compose down -v
```

### 生产环境部署

1. **使用HTTPS**：
   - 配置SSL证书
   - 更新nginx.conf启用HTTPS

2. **数据持久化**：
   - MySQL数据已通过volume持久化
   - Redis数据已通过volume持久化

3. **监控和日志**：
   - 配置Prometheus监控
   - 配置ELK日志收集

---

## 常见问题

### Q1: AI Chatbot提示"AI服务不可用"

**原因**：未配置AI API密钥

**解决**：
1. 检查 `.env` 文件是否配置了 `ANTHROPIC_API_KEY` 或 `OPENAI_API_KEY`
2. 重启后端服务：`docker-compose restart backend`
3. 检查日志：`docker-compose logs backend | grep LLM`

### Q2: 成本异常检测没有数据

**原因**：历史数据不足或账号配置错误

**解决**：
1. 确保至少7天的账单数据
2. 检查账号配置是否正确
3. 确认数据库中有账单数据

### Q3: 预算告警没有发送

**原因**：未配置通知渠道或告警阈值未触发

**解决**：
1. 检查 `.env` 中的通知配置
2. 确认预算使用率是否达到阈值
3. 查看日志：`docker-compose logs backend | grep alert`

### Q4: Docker服务启动失败

**原因**：端口冲突或配置错误

**解决**：
1. 检查端口占用：`lsof -i :3000`、`lsof -i :8000`
2. 修改 `.env` 中的端口配置
3. 查看错误日志：`docker-compose logs`

### Q5: 数据库连接失败

**原因**：数据库未启动或密码错误

**解决**：
1. 检查MySQL容器状态：`docker-compose ps mysql`
2. 确认 `.env` 中的数据库密码正确
3. 重启数据库：`docker-compose restart mysql`

### Q6: 前端页面空白

**原因**：API连接失败或构建错误

**解决**：
1. 检查后端服务是否正常：`curl http://localhost:8000/health`
2. 检查浏览器控制台错误
3. 确认 `NEXT_PUBLIC_API_URL` 配置正确

---

## 获取帮助

- 📖 查看API文档：http://localhost:8000/docs
- 🐛 报告问题：GitHub Issues
- 💬 社区讨论：项目讨论区

---

**最后更新**: 2026-01-17
