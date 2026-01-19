# CloudLens 更新指南

> **版本**: 1.0  
> **更新日期**: 2026-01-19  
> **适用对象**: 已安装 CloudLens 的用户

---

## 🚀 快速更新（推荐）

### 方式1: 使用智能启动脚本（最简单）

```bash
cd cloudlens
./scripts/start.sh
```

脚本会自动：
1. ✅ 检测代码是否有更新
2. ✅ 询问是否拉取最新代码
3. ✅ 检测运行中的服务
4. ✅ 询问是否重启服务
5. ✅ 拉取最新镜像
6. ✅ 启动服务

**这是最简单的方式，推荐所有用户使用！**

---

## 📋 手动更新步骤

### 步骤 1: 拉取最新代码

```bash
cd cloudlens
git pull origin main
```

### 步骤 2: 更新并重启服务

**方式A: 使用智能启动脚本（推荐）**

```bash
./scripts/start.sh
```

脚本会：
- 自动检测运行中的服务
- 询问是否要重启
- 拉取最新镜像
- 启动服务

**方式B: 手动操作**

```bash
# 1. 停止现有服务
docker compose down

# 2. 拉取最新镜像
docker compose pull

# 3. 启动服务
docker compose up -d
```

---

## 🔄 不同场景的更新方式

### 场景1: 代码更新（功能更新、Bug修复）

```bash
cd cloudlens
git pull origin main
./scripts/start.sh
```

选择 `y` 重启服务以应用更新。

### 场景2: 仅镜像更新（Docker 镜像有新版本）

```bash
cd cloudlens
./scripts/start.sh
```

如果服务正在运行，选择：
- `y` - 重启服务使用新镜像
- `n` - 仅拉取镜像，稍后手动重启

### 场景3: 代码和镜像都更新

```bash
cd cloudlens
git pull origin main
./scripts/start.sh
```

脚本会自动处理所有步骤。

---

## ⚠️ 注意事项

### 1. 数据安全

更新前建议备份重要数据：

```bash
# 备份数据库（如果使用 Docker）
docker compose exec mysql mysqldump -u cloudlens -pcloudlens123 cloudlens > backup_$(date +%Y%m%d).sql

# 备份配置文件
cp ~/.cloudlens/config.json ~/.cloudlens/config.json.backup
```

### 2. 服务中断

更新过程中服务会短暂中断（约 30-60 秒），请选择合适的时间进行更新。

### 3. 环境变量

如果更新后添加了新的环境变量，需要更新 `.env` 文件：

```bash
# 查看是否有新的环境变量示例
cat .env.example

# 更新 .env 文件
nano .env
```

### 4. 数据库迁移

如果更新包含数据库结构变更，服务启动时会自动执行迁移，无需手动操作。

---

## 🐛 更新后问题排查

### 问题1: 服务无法启动

```bash
# 查看服务状态
docker compose ps

# 查看日志
docker compose logs

# 查看特定服务日志
docker compose logs backend
docker compose logs frontend
```

### 问题2: 镜像拉取失败

```bash
# 手动拉取镜像
docker compose pull

# 如果拉取失败，使用本地构建
docker compose build
docker compose up -d
```

### 问题3: 代码冲突

如果 `git pull` 出现冲突：

```bash
# 查看冲突文件
git status

# 备份本地更改
git stash

# 拉取最新代码
git pull origin main

# 恢复本地更改（如果需要）
git stash pop
```

---

## 📚 相关文档

- [用户快速开始指南](./QUICK_START_FOR_USERS.md)
- [开发者快速开始指南](./QUICK_START_FOR_DEVELOPERS.md)
- [故障排查指南](./QUICK_START_FOR_USERS.md#故障排查)

---

**最后更新**: 2026-01-19  
**维护者**: CloudLens Team
