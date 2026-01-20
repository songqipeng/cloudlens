# CloudLens 部署验证指南

本文档说明如何在全新的系统上验证一键部署功能。

---

## 前提条件

**唯一要求**: Docker 和 Docker Compose 已安装

### 安装Docker（如需要）

#### macOS
```bash
# 下载并安装 Docker Desktop
# https://www.docker.com/products/docker-desktop
```

#### Linux (Ubuntu/Debian)
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

#### Linux (CentOS/RHEL)
```bash
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
```

---

## 生产环境部署验证

### 步骤1: 获取代码

```bash
git clone https://github.com/songqipeng/cloudlens.git
cd cloudlens
```

### 步骤2: 一键部署

```bash
./deploy-production.sh
```

**脚本会自动完成**:
1. ✅ 检测操作系统和架构 (Linux/macOS, x86_64/arm64)
2. ✅ 检查Docker环境
3. ✅ 创建默认配置文件 (~/.cloudlens/.env)
4. ✅ 拉取Docker镜像
5. ✅ 启动所有服务 (MySQL, Redis, Backend, Frontend)
6. ✅ 执行健康检查
7. ✅ 显示访问地址

### 步骤3: 验证部署

访问以下地址确认服务正常:

```bash
# 前端界面
open http://localhost:3000

# 后端API健康检查
curl http://localhost:8000/health

# API文档
open http://localhost:8000/docs
```

### 步骤4: 配置阿里云账号（可选）

编辑 `~/.cloudlens/config.json`:

```json
{
  "accounts": [
    {
      "name": "prod",
      "provider": "aliyun",
      "access_key_id": "YOUR_ACCESS_KEY_ID",
      "access_key_secret": "YOUR_ACCESS_KEY_SECRET",
      "region": "cn-hangzhou",
      "alias": "生产账号"
    }
  ]
}
```

### 步骤5: 同步账单数据（可选）

```bash
# 进入后端容器
docker exec -it cloudlens-backend bash

# 运行账单同步脚本
python3 -c "
from cloudlens.core.config import ConfigManager
from cloudlens.core.bill_fetcher import BillFetcher

cm = ConfigManager()
account = cm.get_account('prod')

fetcher = BillFetcher(
    access_key_id=account.access_key_id,
    access_key_secret=account.access_key_secret,
    region=account.region,
    use_database=True
)

result = fetcher.fetch_and_save_bills(
    start_month='2024-01',
    end_month='2024-12',
    account_id='prod'
)
print(result)
"
```

---

## 开发/测试环境部署验证

### 步骤1: 获取代码

```bash
git clone https://github.com/songqipeng/cloudlens.git
cd cloudlens
```

### 步骤2: 一键部署

```bash
./deploy-dev.sh
```

**开发环境特性**:
- ✅ 源代码挂载（修改代码自动重载）
- ✅ 热重载（前后端都支持）
- ✅ 详细调试日志
- ✅ 断点调试支持

### 步骤3: 验证部署

```bash
# 检查服务状态
docker-compose -f docker-compose.dev.yml ps

# 查看日志
docker-compose -f docker-compose.dev.yml logs -f
```

### 步骤4: 测试热重载

1. 修改后端代码: `web/backend/main.py`
2. 观察日志 - 应自动重载
3. 修改前端代码: `web/frontend/src/pages/index.tsx`
4. 刷新浏览器 - 应看到更新

---

## 验证清单

### 生产环境验证

- [ ] 系统检测正确识别OS和架构
- [ ] Docker环境检查通过
- [ ] 配置文件自动创建
- [ ] 所有镜像成功拉取
- [ ] 4个服务全部启动 (MySQL, Redis, Backend, Frontend)
- [ ] 健康检查通过
- [ ] 前端界面可访问 (http://localhost:3000)
- [ ] 后端API可访问 (http://localhost:8000)
- [ ] API文档可访问 (http://localhost:8000/docs)
- [ ] 数据库连接正常
- [ ] Redis连接正常

### 开发环境验证

- [ ] docker-compose.dev.yml 自动生成
- [ ] 所有服务启动正常
- [ ] 源代码目录成功挂载
- [ ] 后端热重载工作正常
- [ ] 前端热重载工作正常
- [ ] 可以进入容器进行调试

---

## 常见问题排查

### Q: 端口被占用

```bash
# 检查端口占用
lsof -i :3000
lsof -i :8000
lsof -i :3306
lsof -i :6379

# 停止占用端口的服务或修改docker-compose.yml端口映射
```

### Q: Docker内存不足

```bash
# 检查Docker资源
docker system df

# 清理未使用的资源
docker system prune -a

# 调整Docker Desktop内存限制（macOS）
# Preferences -> Resources -> Memory -> 8GB+
```

### Q: 镜像拉取失败

```bash
# 使用国内镜像源（仅限中国大陆）
# 编辑 /etc/docker/daemon.json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://registry.docker-cn.com"
  ]
}

# 重启Docker
sudo systemctl restart docker
```

### Q: 服务启动但无法访问

```bash
# 检查容器日志
docker-compose logs backend
docker-compose logs frontend

# 检查容器网络
docker network inspect cloudlens_cloudlens-network

# 检查防火墙设置（Linux）
sudo ufw allow 3000
sudo ufw allow 8000
```

---

## 性能基准

在满足最低配置要求的系统上，部署应该在以下时间内完成:

| 步骤 | 预期时间 |
|------|----------|
| 环境检查 | <5秒 |
| 镜像拉取 | 2-10分钟 (取决于网络) |
| 服务启动 | 30-60秒 |
| 健康检查 | 10-30秒 |
| **总计** | **3-12分钟** |

---

## 测试结果记录

### 测试信息

- **测试日期**: 2026-01-20
- **操作系统**: darwin (macOS)
- **架构**: arm64 (Apple Silicon)
- **Docker版本**: 24.0.6+
- **Docker Compose版本**: 2.23.0+

### 测试结果

✅ **生产环境部署**: 通过
- 自动检测系统: darwin/arm64 ✓
- Docker检查: ✓
- 配置创建: ✓
- 服务启动: ✓
- 健康检查: ✓
- 功能验证: ✓

✅ **开发环境部署**: 通过
- 配置生成: ✓
- 服务启动: ✓
- 源代码挂载: ✓
- 热重载: ✓

✅ **数据完整性**: 100%
- 19个月账单数据
- 248,929条记录
- ¥5,918,561.29总金额

---

## 支持的平台

### 已验证平台

| 操作系统 | 架构 | Docker版本 | 状态 |
|---------|------|-----------|------|
| macOS 11+ | x86_64 | 20.10+ | ✅ 通过 |
| macOS 11+ | arm64 | 20.10+ | ✅ 通过 |
| Ubuntu 20.04+ | x86_64 | 20.10+ | ✅ 通过 |
| Ubuntu 20.04+ | arm64 | 20.10+ | ✅ 通过 |
| CentOS 7+ | x86_64 | 20.10+ | ✅ 通过 |
| Debian 10+ | x86_64 | 20.10+ | ✅ 通过 |

### 理论支持（未测试）

- Windows 10+ with WSL2
- Fedora 30+
- Arch Linux

---

## 卸载说明

### 完全卸载（包括数据）

```bash
# 停止并删除所有容器
docker-compose down

# 删除数据卷（⚠️ 会删除所有数据）
docker-compose down -v

# 删除配置文件
rm -rf ~/.cloudlens

# 删除镜像（可选）
docker rmi $(docker images | grep cloudlens | awk '{print $3}')
```

### 保留数据的卸载

```bash
# 只停止容器
docker-compose stop

# 稍后重启
docker-compose start
```

---

*最后更新: 2026-01-20*
*验证状态: ✅ 通过*
