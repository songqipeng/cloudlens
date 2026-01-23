# CloudLens AWS部署检查清单

## 📋 部署前准备

### ✅ 必需信息

- [ ] **AWS账户和凭证**
  - AWS Access Key ID
  - AWS Secret Access Key
  - 默认区域（推荐: us-east-1）

- [ ] **域名信息**
  - 域名: `cloudlens.songqipeng.com`
  - 父域名: `songqipeng.com`
  - 域名是否已在Route 53: □ 是  □ 否

- [ ] **SSH密钥**
  - 已有SSH密钥对: □ 是  □ 否
  - 如果否，需要生成: `ssh-keygen -t rsa -b 4096`

- [ ] **数据库密码**
  - 准备一个强密码（至少16位，包含大小写字母、数字、特殊字符）

---

## 🚀 部署步骤

### 步骤1: 环境准备

```bash
# 1. 安装Terraform
brew install terraform  # macOS
# 或从官网下载: https://www.terraform.io/downloads

# 2. 安装AWS CLI
brew install awscli  # macOS
# 或: pip install awscli

# 3. 配置AWS凭证
aws configure
# 输入您的AWS凭证

# 4. 运行环境设置脚本
cd /path/to/cloudlens
./scripts/setup-terraform.sh
```

### 步骤2: 配置Terraform变量

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars  # 或使用您喜欢的编辑器
```

**必需配置项**:

```hcl
# 1. AWS区域
aws_region = "us-east-1"  # 或您偏好的区域

# 2. 域名配置
domain_name = "cloudlens.songqipeng.com"
route53_zone_name = "songqipeng.com"
create_route53_zone = false  # 如果域名已在Route 53，设为false

# 3. SSH密钥（二选一）
# 选项A: 自动创建
create_key_pair = true
ssh_public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ... your-email@example.com"

# 选项B: 使用现有
# create_key_pair = false
# existing_key_name = "my-existing-key"

# 4. 数据库密码（请修改为强密码）
mysql_password = "YOUR_SECURE_PASSWORD_HERE"
```

### 步骤3: 初始化Terraform

```bash
cd terraform
terraform init
```

### 步骤4: 检查部署计划

```bash
terraform plan
```

**检查要点**:
- [ ] 实例类型正确（t3.medium）
- [ ] 域名配置正确
- [ ] 安全组规则合理
- [ ] 没有意外创建的资源

### 步骤5: 部署

```bash
terraform apply
```

输入 `yes` 确认。

**预计时间**: 10-15分钟

### 步骤6: 等待DNS传播

如果域名不在Route 53，需要：

1. **获取名称服务器**:
```bash
terraform output route53_zone_name_servers
```

2. **在DNS服务商配置**:
   - 登录您的DNS服务商（如阿里云域名控制台）
   - 找到 `songqipeng.com` 域名
   - 修改名称服务器为Terraform输出的值
   - 等待DNS传播（通常几分钟到几小时）

### 步骤7: 验证部署

```bash
# 1. 查看输出
terraform output

# 2. SSH连接到实例
terraform output ssh_command

# 3. 检查服务状态
ssh -i ~/.ssh/cloudlens-key.pem ec2-user@<instance-ip>
cd /opt/cloudlens/app
docker-compose ps
docker-compose logs -f

# 4. 访问应用
# 打开浏览器: https://cloudlens.songqipeng.com
```

---

## 🔧 域名配置说明

### 情况A: 域名已在Route 53

如果 `songqipeng.com` 已经在AWS Route 53中：

```hcl
route53_zone_name = "songqipeng.com"
create_route53_zone = false
```

**Terraform会自动**:
- ✅ 查找现有托管区域
- ✅ 创建 `cloudlens.songqipeng.com` A记录
- ✅ 配置SSL证书DNS验证记录
- ✅ 无需手动操作

### 情况B: 域名在其他DNS服务商

如果域名在阿里云、腾讯云等其他服务商：

1. **在Terraform中创建Route 53托管区域**:
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
   - 登录DNS服务商控制台
   - 找到 `songqipeng.com` 域名
   - 修改名称服务器为Terraform输出的值
   - 例如:
     ```
     ns-123.awsdns-12.com
     ns-456.awsdns-45.net
     ns-789.awsdns-78.org
     ns-012.awsdns-01.co.uk
     ```

4. **等待DNS传播**:
   - 通常需要几分钟到几小时
   - 可以使用 `dig` 命令检查:
     ```bash
     dig NS songqipeng.com
     ```

---

## ⚠️ 常见问题

### Q1: SSL证书验证失败

**原因**: DNS记录未正确配置或未传播

**解决**:
1. 检查Route 53记录: AWS控制台 → Route 53
2. 检查DNS传播: `dig cloudlens.songqipeng.com`
3. 等待DNS传播（最多48小时，通常几分钟）

### Q2: 无法SSH连接

**检查**:
1. 安全组是否开放22端口
2. 密钥文件权限: `chmod 400 ~/.ssh/cloudlens-key.pem`
3. 使用正确的用户: `ec2-user` (Amazon Linux)

### Q3: 服务无法访问

**检查**:
1. ALB状态: AWS控制台 → EC2 → 负载均衡器
2. 目标组健康检查: 确保实例健康
3. 安全组规则: 确保ALB可以访问EC2的8000和3000端口

---

## 📊 部署后验证

### 1. 检查所有服务

```bash
# SSH连接
ssh -i ~/.ssh/cloudlens-key.pem ec2-user@<instance-ip>

# 检查Docker服务
docker ps
docker-compose ps

# 检查日志
docker-compose logs backend
docker-compose logs frontend
docker-compose logs mysql
```

### 2. 检查健康状态

```bash
# 后端健康检查
curl https://cloudlens.songqipeng.com/api/health

# 前端访问
curl -I https://cloudlens.songqipeng.com
```

### 3. 检查SSL证书

```bash
# 检查证书
openssl s_client -connect cloudlens.songqipeng.com:443 -servername cloudlens.songqipeng.com
```

---

## 🔒 安全建议

### 部署后立即执行

1. **修改默认密码**:
   - 修改MySQL root密码
   - 修改应用数据库密码

2. **限制SSH访问**:
   - 修改安全组，限制SSH为特定IP
   - 或使用AWS Systems Manager Session Manager

3. **配置备份**:
   - 设置EBS快照自动备份
   - 配置RDS自动备份（如果使用RDS）

4. **监控告警**:
   - 配置CloudWatch告警
   - 设置成本预算告警

---

## 📝 需要您提供的信息

### 必需信息

1. **AWS凭证**
   - Access Key ID
   - Secret Access Key
   - 默认区域

2. **域名信息**
   - 域名是否已在Route 53: □ 是  □ 否
   - 如果否，需要DNS服务商访问权限

3. **SSH密钥**
   - 已有密钥对: □ 是  □ 否
   - 如果否，我可以帮您生成

### 可选信息

- 偏好的AWS区域（默认: us-east-1）
- 实例类型偏好（默认: t3.medium）
- 存储大小（默认: 50GB）

---

## 🎯 快速部署命令

```bash
# 1. 环境准备
./scripts/setup-terraform.sh

# 2. 配置变量
cd terraform
cp terraform.tfvars.example terraform.tfvars
# 编辑 terraform.tfvars

# 3. 部署
terraform init
terraform plan
terraform apply

# 4. 查看输出
terraform output
```

---

*最后更新: 2026-01-23*
