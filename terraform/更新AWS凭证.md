# 更新 AWS 凭证

## ⚠️ 当前状态

之前的 Access Key 可能已失效，需要更新凭证。

---

## 🔑 获取新的 Access Key

### 步骤1：登录 AWS 控制台

访问: https://console.aws.amazon.com/iam

### 步骤2：创建新的访问密钥

1. 点击左侧菜单 "用户" (Users)
2. 点击您的用户名 `songqipeng`
3. 点击 "安全凭证" (Security credentials) 标签页
4. 滚动到 "访问密钥" (Access keys) 部分
5. 点击 "创建访问密钥" (Create access key)

### 步骤3：选择用途

- 选择 "命令行界面 (CLI)" 或 "应用程序在 AWS 外部运行"
- 点击 "下一步"
- 点击 "创建访问密钥"

### 步骤4：保存密钥 ⚠️ 重要！

会显示两个值：
- **Access Key ID**: 类似 `AKIAIOSFODNN7EXAMPLE`
- **Secret Access Key**: 类似 `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`

⚠️ **Secret Access Key 只显示一次，请立即保存！**

---

## 🚀 配置新凭证

### 方法1：使用配置脚本

```bash
cd terraform
./配置AWS凭证.sh
```

脚本会引导您输入新的 Access Key ID 和 Secret Access Key。

### 方法2：手动配置

```bash
aws configure
# 输入新的 Access Key ID 和 Secret Access Key
# 区域: ap-northeast-1 (日本) 或 ap-east-1 (香港)
# 格式: json
```

### 方法3：直接设置

```bash
aws configure set aws_access_key_id "YOUR_NEW_ACCESS_KEY_ID"
aws configure set aws_secret_access_key "YOUR_NEW_SECRET_ACCESS_KEY"
aws configure set default.region ap-northeast-1
```

---

## ✅ 验证配置

配置完成后，运行：

```bash
aws sts get-caller-identity
```

应该显示：
```json
{
    "UserId": "...",
    "Account": "329435385384",
    "Arn": "arn:aws:iam::329435385384:user/songqipeng"
}
```

---

## 📝 注意事项

1. **Secret Access Key 只显示一次**，请立即保存
2. 如果忘记 Secret Key，需要删除旧的 Access Key 并创建新的
3. 建议定期轮换 Access Key 以提高安全性

---

*最后更新: 2026-01-23*
