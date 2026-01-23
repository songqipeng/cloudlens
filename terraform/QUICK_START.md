# CloudLens AWS快速部署指南

**目标**: 在AWS上部署CloudLens，使用域名 `cloudlens.songqipeng.com`

---

## 🚀 5分钟快速开始

### 步骤1: 准备AWS凭证

```bash
# 安装AWS CLI（如果还没有）
brew install awscli  # macOS

# 配置AWS凭证
aws configure
# 输入:
# - AWS Access Key ID: <您的Access Key>
# - AWS Secret Access Key: <您的Secret Key>
# - Default region: us-east-1 (或您偏好的区域)
# - Default output format: json
```

### 步骤2: 准备SSH密钥

```bash
# 如果还没有SSH密钥，生成一个
ssh-keygen -t rsa -b 4096 -C "your-email@example.com" -f ~/.ssh/cloudlens-key

# 查看公钥（稍后需要）
cat ~/.ssh/cloudlens-key.pub
```

### 步骤3: 运行环境设置脚本

```bash
cd /path/to/cloudlens
./scripts/setup-terraform.sh
```

这个脚本会：
- ✅ 检查Terraform和AWS CLI
- ✅ 验证AWS凭证
- ✅ 创建 `terraform.tfvars` 文件
- ✅ 初始化Terraform

### 步骤4: 配置Terraform变量

```bash
cd terraform
nano terraform.tfvars  # 或使用您喜欢的编辑器
```

**最小配置**（复制并修改）:

```hcl
# AWS区域
aws_region = "us-east-1"

# 域名配置
domain_name = "cloudlens.songqipeng.com"
route53_zone_name = "songqipeng.com"
create_route53_zone = false  # 如果域名已在Route 53，设为false

# SSH密钥（使用刚才生成的公钥）
create_key_pair = true
ssh_public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ... your-email@example.com"

# 数据库密码（请修改为强密码！）
mysql_password = "YOUR_SECURE_PASSWORD_HERE"
```

### 步骤5: 部署

```bash
cd terraform

# 检查部署计划
terraform plan

# 如果一切正常，执行部署
terraform apply
```

输入 `yes` 确认。

**预计时间**: 10-15分钟

### 步骤6: 获取访问信息

```bash
# 查看所有输出
terraform output

# 访问域名
terraform output domain_name
# 输出: https://cloudlens.songqipeng.com
```

---

## 🌐 域名配置说明

### 情况A: 域名已在Route 53（最简单）

如果 `songqipeng.com` 已经在AWS Route 53中：

```hcl
route53_zone_name = "songqipeng.com"
create_route53_zone = false
```

**Terraform会自动完成**:
- ✅ 查找现有托管区域
- ✅ 创建 `cloudlens.songqipeng.com` A记录
- ✅ 配置SSL证书DNS验证
- ✅ **无需任何手动操作**

### 情况B: 域名在其他DNS服务商

如果域名在阿里云、腾讯云等其他服务商：

1. **在terraform.tfvars中设置**:
```hcl
create_route53_zone = true
route53_zone_name = "songqipeng.com"
```

2. **部署后获取名称服务器**:
```bash
terraform apply
terraform output route53_zone_name_servers
```

3. **在您的DNS服务商配置名称服务器**:
   - 登录DNS服务商控制台（如阿里云域名控制台）
   - 找到 `songqipeng.com` 域名
   - 修改名称服务器为Terraform输出的4个NS记录
   - 等待DNS传播（通常几分钟）

4. **验证DNS传播**:
```bash
dig NS songqipeng.com
# 应该显示AWS的名称服务器
```

---

## 📋 需要您提供的信息

### 必需信息

1. **AWS凭证**
   - Access Key ID
   - Secret Access Key
   - 区域（推荐: us-east-1）

2. **域名信息**
   - 域名是否已在Route 53: □ 是  □ 否
   - 如果否，需要DNS服务商访问权限

3. **SSH公钥**
   - 运行 `cat ~/.ssh/cloudlens-key.pub` 获取

4. **数据库密码**
   - 准备一个强密码（至少16位）

### 可选配置

- 实例类型（默认: t3.medium，可改为t3.small节省成本）
- 存储大小（默认: 50GB）
- AWS区域（默认: us-east-1）

---

## ✅ 部署后验证

### 1. 检查服务状态

```bash
# 获取SSH命令
terraform output ssh_command

# SSH连接
ssh -i ~/.ssh/cloudlens-key.pem ec2-user@<instance-ip>

# 检查服务
cd /opt/cloudlens/app
docker-compose ps
docker-compose logs -f
```

### 2. 访问应用

打开浏览器: `https://cloudlens.songqipeng.com`

### 3. 检查SSL证书

证书会自动配置，如果访问时显示"不安全"，可能需要等待几分钟让证书生效。

---

## 🐛 故障排查

### 问题1: SSL证书验证失败

**症状**: Terraform apply时证书验证失败

**解决**:
1. 检查Route 53记录是否正确创建
2. 等待DNS传播（最多48小时，通常几分钟）
3. 检查域名是否正确指向Route 53

### 问题2: 无法访问网站

**检查**:
1. ALB状态: AWS控制台 → EC2 → 负载均衡器
2. 目标组健康检查: 确保实例健康
3. 安全组: 确保ALB可以访问EC2

### 问题3: SSH连接失败

**检查**:
1. 安全组是否开放22端口
2. 密钥文件权限: `chmod 400 ~/.ssh/cloudlens-key.pem`
3. 使用正确的用户: `ec2-user`

---

## 💰 成本估算

基于 `us-east-1` 区域，t3.medium配置：

| 资源 | 月成本 |
|------|--------|
| EC2 t3.medium | $30 |
| EBS 50GB | $4 |
| ALB | $16 |
| 数据传输 | $0-10 |
| **总计** | **约 $50-60/月** |

---

## 📚 更多信息

- [完整部署指南](./README.md)
- [部署检查清单](./DEPLOYMENT_CHECKLIST.md)
- [AWS部署方案对比](../docs/AWS_DEPLOYMENT_GUIDE.md)

---

*最后更新: 2026-01-23*
