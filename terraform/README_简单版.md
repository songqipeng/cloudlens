# CloudLens 超简单部署指南

**3步完成部署，10分钟搞定！**

---

## 🎯 第一步：申请 AWS 密钥

### 方法：通过网页（最简单）

1. **打开 AWS 控制台**
   - 访问: https://console.aws.amazon.com
   - 登录您的账户

2. **找到 IAM**
   - 在顶部搜索框输入 "IAM"，点击进入

3. **创建访问密钥**
   - 点击左侧 "用户" → 点击您的用户名
   - 点击 "安全凭证" 标签
   - 找到 "访问密钥" 部分
   - 点击 "创建访问密钥"

4. **保存密钥** ⚠️ 重要！
   - 会显示两个值：
     - **Access Key ID**: 类似 `AKIAIOSFODNN7EXAMPLE`
     - **Secret Access Key**: 类似 `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`
   - ⚠️ **Secret 只显示一次，立即保存！**
   - 点击 "下载 .csv" 保存到本地

5. **配置到本地**
   ```bash
   aws configure
   # 输入刚才保存的两个密钥
   # 区域输入: ap-northeast-1 (日本) 或 ap-east-1 (香港)
   # 格式输入: json
   ```

---

## 🚀 第二步：一键部署

### 方法1：使用一键脚本（最简单）

```bash
cd terraform
./一键部署.sh
```

脚本会自动：
- ✅ 检查环境
- ✅ 创建配置文件
- ✅ 引导您填写配置
- ✅ 自动部署

### 方法2：手动部署（3个命令）

```bash
# 1. 准备配置
cd terraform
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars  # 填写配置（见下方）

# 2. 初始化
terraform init

# 3. 部署
terraform apply
```

---

## 📝 配置文件说明

编辑 `terraform.tfvars`，只需要改这几行：

```hcl
# 1. 选择区域（日本或香港）
aws_region = "ap-northeast-1"  # 日本东京（推荐）
# 或
# aws_region = "ap-east-1"     # 香港

# 2. 域名（通常不用改）
domain_name = "cloudlens.songqipeng.com"
route53_zone_name = "songqipeng.com"
create_route53_zone = false  # 如果域名已在Route 53

# 3. SSH公钥（运行 cat ~/.ssh/id_rsa.pub 获取）
create_key_pair = true
ssh_public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ... your-email@example.com"

# 4. 数据库密码（改成强密码！）
mysql_password = "YourSecurePassword123!@#"
```

---

## ✅ 第三步：等待完成

部署需要 **10-15分钟**，完成后会显示：

```
✅ 部署完成！
访问地址: https://cloudlens.songqipeng.com
```

---

## 🌏 区域选择

### 日本（ap-northeast-1）- 推荐

**优势**:
- ✅ 延迟低
- ✅ 价格适中（约 ¥7,500/月）
- ✅ 服务齐全

### 香港（ap-east-1）

**优势**:
- ✅ 延迟最低
- ⚠️ 价格稍高（约 ¥8,400/月）

---

## 🐛 常见问题

### Q: 找不到 IAM？

**A**: 在 AWS 控制台顶部搜索框输入 "IAM" 即可

### Q: 创建密钥时提示权限不足？

**A**: 
- 联系账户管理员
- 或使用根账户（不推荐）

### Q: 部署失败？

**A**: 
1. 检查 AWS 凭证: `aws sts get-caller-identity`
2. 检查配置是否正确
3. 查看错误信息

---

## 💰 费用

**日本**: 约 ¥7,500/月 (~$50)  
**香港**: 约 ¥8,400/月 (~$56)

---

## 📞 需要帮助？

查看详细文档:
- [完整指南](./README.md)
- [简单部署指南](./简单部署指南.md)

---

*最后更新: 2026-01-23*
