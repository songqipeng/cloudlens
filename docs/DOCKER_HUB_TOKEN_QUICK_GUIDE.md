# Docker Hub Access Token 快速创建指南

> **快速链接**: https://hub.docker.com/settings/security

---

## 🚀 最快方式：直接访问

**直接点击或复制以下链接**：
```
https://hub.docker.com/settings/security
```

---

## 📝 创建步骤

### 1. 打开 Security 页面

- **方法 A**: 直接访问上面的链接
- **方法 B**: 从 Docker Hub 首页 → 点击右上角头像 → Account Settings → Security

### 2. 创建 Access Token

1. 在 Security 页面，找到 **"New Access Token"** 部分
2. 填写信息：
   - **Description**: `GitHub Actions CloudLens`（或任何您喜欢的描述）
   - **Access permissions**: 选择 **"Read & Write"**
3. 点击 **"Generate"** 按钮

### 3. 复制 Token

⚠️ **重要**: Token 只显示一次！

- 立即复制生成的 Token
- Token 格式类似：`dckr_pat_xxxxxxxxxxxxxxxxxxxxxxxxxx`
- 保存到安全的地方（密码管理器、文本文件等）

### 4. 在 GitHub 中添加

1. 访问：https://github.com/songqipeng/cloudlens/settings/secrets/actions
2. 点击 **"New repository secret"**
3. 填写：
   - **Name**: `DOCKER_HUB_TOKEN`（必须完全一致）
   - **Secret**: 粘贴刚才复制的 Token
4. 点击 **"Add secret"**

---

## 🔍 如果找不到 Security 页面

### 检查点：

1. ✅ 确认已登录 Docker Hub
2. ✅ 确认使用的是正确的账号（songqipeng）
3. ✅ 尝试直接访问：https://hub.docker.com/settings/security

### 替代方法：

如果 Security 页面不可见，可能是：
- 账号类型限制（某些免费账号可能没有此功能）
- 需要升级到付费计划

**解决方案**：
- 检查账号类型
- 或联系 Docker Hub 支持

---

## ✅ 验证 Token 是否有效

创建 Token 后，可以测试：

```bash
# 使用 Token 登录（测试）
echo "YOUR_TOKEN" | docker login -u songqipeng --password-stdin
```

如果登录成功，说明 Token 有效。

---

## 📚 相关文档

- [完整配置指南](./DOCKER_HUB_GITHUB_SETUP.md)
- [Docker Hub 使用指南](./DOCKER_HUB_SETUP.md)

---

**最后更新**: 2026-01-19
