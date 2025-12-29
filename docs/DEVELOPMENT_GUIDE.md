# 开发指南

> CloudLens 开发环境搭建与开发规范  
> 最后更新：2025-12-23

---

## 📋 目录

- [环境要求](#环境要求)
- [开发环境搭建](#开发环境搭建)
- [代码规范](#代码规范)
- [Git 工作流](#git-工作流)
- [调试技巧](#调试技巧)
- [常见问题](#常见问题)
- [项目结构](#项目结构)

---

## 环境要求

### 必需软件

- **Python**: 3.9+ （推荐 3.10+）
- **Node.js**: 18+ （用于前端开发）
- **MySQL**: 5.7+ 或 8.0+ （可选，默认使用 SQLite）
- **Git**: 2.0+

### 推荐工具

- **IDE**: VS Code / PyCharm
- **数据库管理**: MySQL Workbench / DBeaver
- **API 测试**: Postman / Insomnia / curl

---

## 开发环境搭建

### 1. 克隆项目

```bash
git clone https://github.com/songqipeng/aliyunidle.git
cd aliyunidle
```

### 2. Python 环境

#### 创建虚拟环境

```bash
# 使用 venv
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
```

#### 安装依赖

```bash
# 安装生产依赖
pip install -r requirements.txt

# 安装开发依赖
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio black flake8 mypy bandit pre-commit
```

### 3. 前端环境

```bash
cd web/frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 4. 配置项目

#### 创建配置文件

```bash
# 创建配置目录
mkdir -p ~/.cloudlens

# 复制示例配置
cp config.json.example ~/.cloudlens/config.json

# 编辑配置
vim ~/.cloudlens/config.json
```

#### 配置示例

```json
{
  "accounts": [
    {
      "name": "test",
      "alias": "测试账号",
      "provider": "aliyun",
      "region": "cn-beijing",
      "access_key_id": "your_access_key_id",
      "access_key_secret": "your_access_key_secret"
    }
  ],
  "database": {
    "type": "sqlite",
    "path": "data/db/cloudlens.db"
  }
}
```

#### MySQL 配置（可选）

如果使用 MySQL，需要创建数据库：

```sql
CREATE DATABASE cloudlens CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

然后更新配置：

```json
{
  "database": {
    "type": "mysql",
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "your_password",
    "database": "cloudlens"
  }
}
```

### 5. 初始化数据库

```bash
# 如果使用 MySQL，运行初始化脚本
mysql -u root -p cloudlens < sql/init_mysql_schema.sql

# 验证 Schema
python sql/verify_schema.py
```

### 6. 启动服务

#### 启动后端

```bash
cd web/backend
python -m uvicorn main:app --reload --port 8000
```

#### 启动前端（新终端）

```bash
cd web/frontend
npm run dev
```

访问 `http://localhost:3000` 查看 Web 界面。

---

## 代码规范

### Python 代码风格

#### 1. 遵循 PEP 8

- 使用 4 个空格缩进
- 行长度限制：100 字符
- 使用 `snake_case` 命名函数和变量
- 使用 `PascalCase` 命名类

#### 2. 使用 Black 格式化

```bash
# 格式化所有 Python 文件
black .

# 格式化特定文件
black core/idle_detector.py

# 检查格式（不修改）
black --check .
```

#### 3. 类型提示

所有公共函数都应该包含类型提示：

```python
from typing import List, Dict, Optional

def get_resources(
    account: str,
    resource_type: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    获取资源列表
    
    Args:
        account: 账号名称
        resource_type: 资源类型（可选）
        limit: 返回数量限制
        
    Returns:
        资源列表
    """
    pass
```

#### 4. Docstrings

使用 Google 风格的 Docstrings：

```python
def calculate_cost(
    resources: List[Dict],
    start_date: datetime,
    end_date: datetime
) -> float:
    """
    计算指定时间范围内的资源成本
    
    Args:
        resources: 资源列表
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        总成本（元）
        
    Raises:
        ValueError: 如果日期范围无效
    """
    if start_date > end_date:
        raise ValueError("开始日期不能晚于结束日期")
    # ...
```

### TypeScript 代码风格

#### 1. 使用 ESLint

```bash
cd web/frontend
npm run lint
```

#### 2. 类型定义

```typescript
interface Resource {
  id: string;
  name: string;
  type: string;
  status: string;
  cost: number;
}

function getResources(account: string): Promise<Resource[]> {
  // ...
}
```

### 代码检查

#### 运行所有检查

```bash
# 格式化代码
black .

# 检查代码风格
flake8 .

# 类型检查
mypy core providers

# 安全扫描
bandit -r core providers
```

---

## Git 工作流

### 分支策略

- **main**: 主分支，稳定版本
- **develop**: 开发分支
- **feature/xxx**: 功能分支
- **fix/xxx**: Bug 修复分支
- **docs/xxx**: 文档更新分支

### 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```
<type>(<scope>): <subject>

<body>

<footer>
```

#### Type 类型

- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式调整（不影响功能）
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具链更新

#### 示例

```bash
# 新功能
git commit -m "feat(provider): add AWS provider support"

# Bug 修复
git commit -m "fix(cache): fix cache expiration issue"

# 文档更新
git commit -m "docs: update API reference"

# 重构
git commit -m "refactor(storage): unify storage interface"
```

### Pull Request 流程

1. **创建分支**

```bash
git checkout -b feature/new-feature
```

2. **开发并提交**

```bash
git add .
git commit -m "feat: add new feature"
git push origin feature/new-feature
```

3. **创建 PR**

在 GitHub 上创建 Pull Request，填写：
- 标题：清晰描述功能
- 描述：详细说明变更内容
- 关联 Issue：`Closes #123`

4. **代码审查**

- 等待 CI 通过
- 等待代码审查
- 根据反馈修改

5. **合并**

审查通过后，由维护者合并到主分支。

---

## 调试技巧

### 1. Python 调试

#### 使用 pdb

```python
import pdb

def my_function():
    pdb.set_trace()  # 断点
    # 代码会在这里暂停
    pass
```

#### 使用日志

```python
import logging

logger = logging.getLogger(__name__)

def my_function():
    logger.debug("调试信息")
    logger.info("一般信息")
    logger.warning("警告信息")
    logger.error("错误信息")
```

#### 查看日志

```bash
# 查看后端日志
tail -f logs/backend.log

# 查看前端日志
tail -f logs/frontend.log
```

### 2. 前端调试

#### 使用浏览器开发者工具

- **Chrome DevTools**: F12
- **React DevTools**: 安装浏览器扩展

#### 使用 console

```typescript
console.log("调试信息", data);
console.error("错误信息", error);
console.warn("警告信息", warning);
```

### 3. API 调试

#### 使用 curl

```bash
# GET 请求
curl http://localhost:8000/api/accounts

# POST 请求
curl -X POST http://localhost:8000/api/budgets \
  -H "Content-Type: application/json" \
  -d '{"name": "测试预算", "amount": 1000}'
```

#### 使用 Swagger UI

访问 `http://localhost:8000/docs` 进行交互式 API 测试。

### 4. 数据库调试

#### SQLite

```bash
# 查看数据库
sqlite3 data/db/cloudlens.db

# 执行查询
sqlite3 data/db/cloudlens.db "SELECT * FROM resources LIMIT 10;"
```

#### MySQL

```bash
# 连接数据库
mysql -u root -p cloudlens

# 执行查询
mysql -u root -p cloudlens -e "SELECT * FROM resources LIMIT 10;"
```

---

## 常见问题

### 1. 导入错误

**问题**：`ModuleNotFoundError: No module named 'core'`

**解决方案**：

```bash
# 确保在项目根目录
cd /path/to/aliyunidle

# 确保虚拟环境已激活
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 数据库连接失败

**问题**：`OperationalError: unable to open database file`

**解决方案**：

```bash
# 检查数据库文件路径
ls -la data/db/

# 创建目录
mkdir -p data/db

# 检查权限
chmod 755 data/db
```

### 3. 前端构建失败

**问题**：`npm install` 失败

**解决方案**：

```bash
# 清除缓存
rm -rf node_modules package-lock.json

# 重新安装
npm install

# 如果还有问题，尝试使用 yarn
yarn install
```

### 4. API 请求超时

**问题**：API 请求超时

**解决方案**：

- 检查后端服务是否运行
- 检查网络连接
- 增加超时时间（前端 `lib/api.ts`）

### 5. 缓存问题

**问题**：数据没有更新

**解决方案**：

```bash
# 清除缓存
./cl cache clear

# 或使用 API
curl -X POST http://localhost:8000/api/virtual-tags/clear-cache
```

---

## 项目结构

### 核心目录

```
aliyunidle/
├── core/              # 核心业务逻辑
│   ├── cache.py       # 缓存管理
│   ├── config.py      # 配置管理
│   ├── idle_detector.py  # 闲置检测
│   └── ...
├── cli/               # CLI 命令
│   ├── main.py        # CLI 入口
│   └── commands/     # 命令模块
├── web/               # Web 应用
│   ├── backend/       # FastAPI 后端
│   │   ├── main.py    # 后端入口
│   │   └── api.py     # API 路由
│   └── frontend/      # Next.js 前端
│       ├── app/       # 页面
│       └── components/ # 组件
├── providers/         # 云服务提供商
│   ├── aliyun/        # 阿里云
│   └── tencent/       # 腾讯云
├── resource_modules/  # 资源分析器
│   ├── ecs_analyzer.py
│   └── ...
├── tests/             # 测试
│   ├── core/          # 核心模块测试
│   └── providers/     # Provider 测试
└── docs/              # 文档
```

### 关键文件

- `config.json`: 主配置文件
- `requirements.txt`: Python 依赖
- `pyproject.toml`: Python 项目配置
- `pytest.ini`: 测试配置
- `mypy.ini`: 类型检查配置

---

## 开发检查清单

提交代码前，请确认：

- [ ] 代码遵循项目规范（Black, Flake8）
- [ ] 类型检查通过（mypy）
- [ ] 所有测试通过（pytest）
- [ ] 添加了必要的测试
- [ ] 更新了相关文档
- [ ] Commit message 符合规范
- [ ] 代码已格式化（black）
- [ ] 没有引入安全漏洞（bandit）

---

## 获取帮助

- **GitHub Issues**: [提交问题](https://github.com/songqipeng/aliyunidle/issues)
- **文档**: 查看 `docs/` 目录
- **API 文档**: 访问 `http://localhost:8000/docs`

---

## 相关文档

- [API 参考](API_REFERENCE.md)
- [测试指南](TESTING_GUIDE.md)
- [贡献指南](CONTRIBUTING.md)
- [技术架构](TECHNICAL_ARCHITECTURE.md)

---

**Happy Coding! 🚀**

