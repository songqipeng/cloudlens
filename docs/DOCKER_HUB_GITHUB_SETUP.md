# Docker Hub 和 GitHub 配置指南

> **版本**: 1.0  
> **更新日期**: 2026-01-18  
> **说明**: 本指南将引导您完成 Docker Hub 和 GitHub 的配置，实现自动构建和推送镜像

---

## 📋 配置概览

完成配置后，当您推送代码到 GitHub 的 `main` 分支时，GitHub Actions 会自动：
1. 构建后端和前端 Docker 镜像
2. 推送到 Docker Hub（`songqipeng/cloudlens-backend` 和 `songqipeng/cloudlens-frontend`）
3. 用户可以直接使用 `docker-compose up` 拉取镜像，无需本地构建

---

## 🔐 步骤 1: 创建 Docker Hub Access Token

### 1.1 登录 Docker Hub

1. 打开浏览器，访问：https://hub.docker.com/
2. 使用您的账号登录（如果没有账号，先注册一个）

### 1.2 创建 Access Token

1. 登录后，点击右上角的用户名，选择 **Account Settings**
2. 在左侧菜单中，点击 **Security** 标签
3. 找到 **New Access Token** 部分
4. 填写以下信息：
   - **Description**: `GitHub Actions CloudLens`（描述，方便识别）
   - **Access permissions**: 选择 **Read & Write**（读写权限）
5. 点击 **Generate** 按钮
6. **重要**: 复制生成的 Token（只显示一次，请妥善保存！）
   - Token 格式类似：`dckr_pat_xxxxxxxxxxxxxxxxxxxxxxxxxx`

### 1.3 保存 Token

将 Token 保存到安全的地方（如密码管理器），下一步需要使用。

---

## 🔧 步骤 2: 在 GitHub 中添加 Secret

### 2.1 打开 GitHub 仓库设置

1. 访问您的 GitHub 仓库：https://github.com/songqipeng/cloudlens
2. 点击仓库顶部的 **Settings** 标签

### 2.2 进入 Secrets 配置

1. 在左侧菜单中，找到 **Secrets and variables** → **Actions**
2. 点击进入 Secrets 页面

### 2.3 添加 DOCKER_HUB_TOKEN

1. 点击右上角的 **New repository secret** 按钮
2. 填写以下信息：
   - **Name**: `DOCKER_HUB_TOKEN`（必须完全一致，区分大小写）
   - **Secret**: 粘贴刚才复制的 Docker Hub Access Token
3. 点击 **Add secret** 按钮

### 2.4 验证 Secret 已添加

在 Secrets 列表中应该能看到 `DOCKER_HUB_TOKEN`（值会被隐藏显示为 `••••••••`）

---

## ✅ 步骤 3: 验证配置

### 3.1 检查 GitHub Actions 工作流文件

确认 `.github/workflows/docker-build.yml` 文件存在且配置正确：

```yaml
env:
  DOCKER_HUB_USERNAME: songqipeng
  IMAGE_NAME: cloudlens
```

### 3.2 检查 docker-compose.yml

确认 `docker-compose.yml` 使用正确的镜像名称：

```yaml
backend:
  image: ${DOCKER_HUB_USERNAME:-songqipeng}/cloudlens-backend:${IMAGE_TAG:-latest}

frontend:
  image: ${DOCKER_HUB_USERNAME:-songqipeng}/cloudlens-frontend:${IMAGE_TAG:-latest}
```

---

## 🚀 步骤 4: 测试自动构建

### 4.1 提交并推送代码

```bash
# 确保所有更改已提交
git add -A
git commit -m "chore: 配置Docker Hub自动构建"

# 推送到GitHub
git push origin main
```

### 4.2 查看 GitHub Actions 运行状态

1. 访问：https://github.com/songqipeng/cloudlens/actions
2. 应该能看到新的工作流运行（"Docker Build and Push to Docker Hub"）
3. 点击进入查看详细日志
4. 等待构建完成（通常需要 5-10 分钟）

### 4.3 验证镜像已推送

1. 访问 Docker Hub：https://hub.docker.com/r/songqipeng/cloudlens-backend
2. 应该能看到新推送的镜像
3. 检查标签：应该有 `latest` 和 `main-<commit-sha>` 标签

---

## 🔍 步骤 5: 测试镜像拉取

### 5.1 清理本地镜像（可选）

```bash
# 删除本地构建的镜像（如果有）
docker rmi songqipeng/cloudlens-backend:latest 2>/dev/null || true
docker rmi songqipeng/cloudlens-frontend:latest 2>/dev/null || true
```

### 5.2 测试拉取镜像

```bash
# 拉取后端镜像
docker pull songqipeng/cloudlens-backend:latest

# 拉取前端镜像
docker pull songqipeng/cloudlens-frontend:latest

# 查看镜像
docker images | grep cloudlens
```

### 5.3 使用 docker-compose 启动

```bash
# 确保 .env 文件已配置
cp .env.example .env
# 编辑 .env，至少配置 AI API 密钥

# 启动服务（会自动拉取镜像）
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

---

## 🐛 故障排查

### 问题 1: GitHub Actions 构建失败

**症状**: Actions 日志显示 "unauthorized" 或 "authentication failed"

**解决方案**:
1. 检查 GitHub Secrets 中的 `DOCKER_HUB_TOKEN` 是否正确
2. 检查 Token 是否过期（重新生成一个）
3. 检查 Token 权限是否为 "Read & Write"

### 问题 2: 镜像推送失败

**症状**: 日志显示 "denied: requested access to the resource is denied"

**解决方案**:
1. 确认 Docker Hub 用户名正确（`songqipeng`）
2. 确认 Token 有推送权限
3. 检查仓库名称是否正确（`cloudlens-backend` 和 `cloudlens-frontend`）

### 问题 3: 无法拉取镜像

**症状**: `docker pull` 失败，提示 "pull access denied"

**解决方案**:
1. 确认镜像已成功推送到 Docker Hub
2. 检查镜像名称和标签是否正确
3. 如果是私有仓库，需要先登录：`docker login -u songqipeng`

### 问题 4: 工作流没有触发

**症状**: 推送代码后，Actions 没有运行

**解决方案**:
1. 检查是否推送到 `main` 分支
2. 检查 `.github/workflows/docker-build.yml` 文件是否存在
3. 检查文件语法是否正确（YAML 格式）

---

## 📝 配置检查清单

完成以下检查清单，确保配置正确：

- [ ] Docker Hub 账号已创建并登录
- [ ] Docker Hub Access Token 已创建（Read & Write 权限）
- [ ] Token 已保存到安全位置
- [ ] GitHub Secrets 中已添加 `DOCKER_HUB_TOKEN`
- [ ] `.github/workflows/docker-build.yml` 文件存在且配置正确
- [ ] `docker-compose.yml` 使用正确的镜像名称
- [ ] 代码已推送到 GitHub `main` 分支
- [ ] GitHub Actions 工作流已成功运行
- [ ] Docker Hub 上可以看到推送的镜像
- [ ] 可以成功拉取镜像并启动服务

---

## 🎯 下一步

配置完成后，您可以：

1. **开发新功能**: 推送代码到 `main` 分支，自动构建新镜像
2. **发布版本**: 创建 Git 标签（如 `v1.0.0`），自动构建版本镜像
3. **用户使用**: 用户只需 `docker-compose up` 即可使用最新版本

---

## 📚 相关文档

- [Docker Hub 使用指南](./DOCKER_HUB_SETUP.md)
- [Q1功能使用指南](./Q1_USER_GUIDE.md)
- [本地测试指南](./LOCAL_TESTING_GUIDE.md)

---

**最后更新**: 2026-01-18  
**维护者**: CloudLens Team
