# CloudLens AWS Terraform部署指南

使用Terraform在AWS上自动化部署CloudLens，包括域名配置和HTTPS。

---

## 📋 前置要求

### 1. 安装必要工具

```bash
# 安装Terraform
# macOS
brew install terraform

# 或从官网下载: https://www.terraform.io/downloads
```

### 2. 配置AWS凭证

```bash
# 安装AWS CLI
brew install awscli  # macOS
# 或: pip install awscli

# 配置AWS凭证
aws configure
# 输入:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region (例如: us-east-1)
# - Default output format (json)
```

### 3. 准备SSH密钥

```bash
# 生成SSH密钥对（如果还没有）
ssh-keygen -t rsa -b 4096 -C "your-email@example.com" -f ~/.ssh/cloudlens-key

# 查看公钥
cat ~/.ssh/cloudlens-key.pub
```

---

## 🚀 快速开始

### 步骤1: 配置Terraform变量

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

编辑 `terraform.tfvars`，填写以下信息：

```hcl
# 必需配置
aws_region = "us-east-1"  # 或您偏好的区域
domain_name = "cloudlens.songqipeng.com"
route53_zone_name = "songqipeng.com"
create_route53_zone = false  # 如果域名已在Route 53

# SSH密钥（二选一）
create_key_pair = true
ssh_public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ... your-email@example.com"
# 或使用现有密钥对：
# create_key_pair = false
# existing_key_name = "my-existing-key"

# 数据库密码（请修改为强密码）
mysql_password = "YOUR_SECURE_PASSWORD_HERE"
```

### 步骤2: 初始化Terraform

```bash
cd terraform
terraform init
```

### 步骤3: 检查部署计划

```bash
terraform plan
```

这会显示将要创建的资源。检查无误后继续。

### 步骤4: 部署

```bash
terraform apply
```

输入 `yes` 确认部署。

### 步骤5: 等待部署完成

部署过程大约需要 **10-15分钟**，包括：
- EC2实例启动
- SSL证书申请和验证
- ALB创建
- DNS记录配置

### 步骤6: 查看输出

```bash
terraform output
```

会显示：
- 访问域名: `https://cloudlens.songqipeng.com`
- SSH连接命令
- 实例信息等

---

## 🔧 配置说明

### 域名配置

#### 情况1: 域名已在Route 53

如果 `songqipeng.com` 已经在Route 53中：

```hcl
route53_zone_name = "songqipeng.com"
create_route53_zone = false
```

Terraform会自动：
- 查找现有托管区域
- 创建 `cloudlens.songqipeng.com` A记录
- 配置SSL证书DNS验证

#### 情况2: 域名不在Route 53

如果域名在其他DNS服务商（如阿里云、腾讯云）：

1. **在Terraform中创建Route 53托管区域**:
```hcl
create_route53_zone = true
route53_zone_name = "songqipeng.com"
```

2. **获取名称服务器**:
```bash
terraform apply
terraform output route53_zone_name_servers
```

3. **在您的DNS服务商配置名称服务器**:
   - 登录您的DNS服务商（如阿里云域名控制台）
   - 找到 `songqipeng.com` 域名
   - 修改名称服务器为Terraform输出的名称服务器
   - 等待DNS传播（通常几分钟到几小时）

### SSH密钥配置

#### 选项1: 自动创建密钥对

```hcl
create_key_pair = true
ssh_public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ... your-email@example.com"
```

#### 选项2: 使用现有密钥对

```hcl
create_key_pair = false
existing_key_name = "my-existing-key"  # AWS中已存在的密钥对名称
```

### 实例配置

```hcl
# 推荐配置（平衡性能和成本）
instance_type = "t3.medium"  # 2 vCPU, 4GB RAM
ebs_volume_size = 50  # GB

# 更便宜的配置（如果预算紧张）
instance_type = "t3.small"   # 2 vCPU, 2GB RAM（可能较紧张）
ebs_volume_size = 30  # GB
```

### 网络配置

#### 使用默认VPC（推荐，最简单）

```hcl
create_vpc = false
```

#### 创建新VPC（如果需要隔离）

```hcl
create_vpc = true
vpc_cidr = "10.0.0.0/16"
public_subnet_cidr = "10.0.1.0/24"
```

---

## 📝 部署后的操作

### 1. SSH连接到实例

```bash
# 使用Terraform输出的SSH命令
terraform output ssh_command

# 或手动连接
ssh -i ~/.ssh/cloudlens-key.pem ec2-user@<instance-ip>
```

### 2. 检查服务状态

```bash
cd /opt/cloudlens/app
docker-compose ps
docker-compose logs -f
```

### 3. 访问应用

打开浏览器访问: `https://cloudlens.songqipeng.com`

---

## 🔒 安全配置

### 1. 限制SSH访问

生产环境应该限制SSH访问为特定IP：

```hcl
ssh_allowed_cidrs = ["1.2.3.4/32"]  # 您的IP地址
```

### 2. 修改默认密码

部署后立即修改MySQL密码：

```bash
# SSH连接到实例
ssh -i ~/.ssh/cloudlens-key.pem ec2-user@<instance-ip>

# 修改docker-compose.yml中的密码
cd /opt/cloudlens/app
nano docker-compose.yml  # 修改MYSQL_PASSWORD

# 重启服务
docker-compose down
docker-compose up -d
```

### 3. 配置防火墙

安全组已自动配置，但建议：
- 限制SSH访问为特定IP
- 只开放必要端口（80, 443）

---

## 🛠️ 常用命令

### 查看资源状态

```bash
terraform show
terraform state list
```

### 更新配置

```bash
# 修改terraform.tfvars
terraform plan  # 查看变更
terraform apply  # 应用变更
```

### 销毁资源

```bash
terraform destroy
```

**⚠️ 警告**: 这会删除所有资源，包括数据！

---

## 📊 资源清单

Terraform会创建以下资源：

| 资源类型 | 数量 | 说明 |
|---------|------|------|
| EC2实例 | 1 | t3.medium |
| EBS卷 | 1 | 50GB数据卷 |
| ALB | 1 | Application Load Balancer |
| 安全组 | 2 | EC2和ALB安全组 |
| ACM证书 | 1 | SSL证书 |
| Route 53记录 | 3+ | 域名和证书验证 |
| IAM角色 | 1 | EC2实例角色 |

---

## 💰 成本估算

基于 `us-east-1` 区域：

| 资源 | 月成本 |
|------|--------|
| EC2 t3.medium | $30 |
| EBS 50GB | $4 |
| ALB | $16 |
| 数据传输 | $0-10 |
| **总计** | **约 $50-60/月** |

---

## 🐛 故障排查

### 问题1: SSL证书验证失败

**原因**: DNS记录未正确配置

**解决**:
```bash
# 检查DNS记录
terraform output route53_zone_name_servers

# 在DNS服务商配置名称服务器
# 等待DNS传播（可能需要几分钟到几小时）
```

### 问题2: 服务无法访问

**检查步骤**:
1. 检查实例状态: `terraform show`
2. SSH连接检查: `terraform output ssh_command`
3. 查看日志: `docker-compose logs -f`
4. 检查安全组: AWS控制台 → EC2 → 安全组

### 问题3: 域名无法解析

**检查步骤**:
1. 检查Route 53记录: AWS控制台 → Route 53
2. 检查ALB状态: AWS控制台 → EC2 → 负载均衡器
3. 等待DNS传播（最多48小时，通常几分钟）

---

## 📚 更多信息

- [Terraform AWS Provider文档](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS部署指南](../docs/AWS_DEPLOYMENT_GUIDE.md)
- [CloudLens文档](../README.md)

---

*最后更新: 2026-01-23*
