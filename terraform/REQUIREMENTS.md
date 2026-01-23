# CloudLens AWS部署 - 需要您提供的信息

## 📋 必需信息

### 1. AWS凭证 ⭐

**需要**:
- AWS Access Key ID
- AWS Secret Access Key
- 默认区域（推荐: `us-east-1`）

**如何获取**:
1. 登录AWS控制台
2. 进入 IAM → 用户 → 您的用户
3. 安全凭证 → 创建访问密钥
4. 下载或复制 Access Key ID 和 Secret Access Key

**配置命令**:
```bash
aws configure
# 输入您的凭证
```

---

### 2. 域名信息 ⭐

**需要**:
- 域名: `cloudlens.songqipeng.com`
- 父域名: `songqipeng.com`
- **域名是否已在AWS Route 53**: □ 是  □ 否

**如果域名已在Route 53**:
- ✅ 无需额外操作
- Terraform会自动查找并使用现有托管区域
- 配置: `create_route53_zone = false`

**如果域名在其他DNS服务商**（如阿里云、腾讯云）:
- ⚠️ 需要DNS服务商的访问权限
- Terraform会创建Route 53托管区域
- 您需要在DNS服务商配置名称服务器
- 配置: `create_route53_zone = true`

---

### 3. SSH密钥 ⭐

**需要**: SSH公钥

**如果已有密钥**:
```bash
# 查看公钥
cat ~/.ssh/id_rsa.pub
# 或
cat ~/.ssh/id_ed25519.pub
```

**如果没有密钥**:
```bash
# 生成新密钥
ssh-keygen -t rsa -b 4096 -C "your-email@example.com" -f ~/.ssh/cloudlens-key

# 查看公钥
cat ~/.ssh/cloudlens-key.pub
```

**复制公钥内容**，稍后填入 `terraform.tfvars`

---

### 4. 数据库密码 ⭐

**需要**: 一个强密码（至少16位）

**要求**:
- 至少16个字符
- 包含大小写字母、数字、特殊字符
- 不要使用常见密码

**示例生成**:
```bash
# 生成随机密码（可选）
openssl rand -base64 24
```

---

## 🔧 可选配置

### AWS区域

**默认**: `us-east-1`（美国东部）

**其他推荐区域**:
- `ap-southeast-1` (新加坡) - 适合亚洲用户
- `ap-northeast-1` (东京)
- `eu-west-1` (爱尔兰)

**如何选择**:
- 选择离您最近的区域（降低延迟）
- 或选择成本更低的区域

### 实例类型

**默认**: `t3.medium` (2 vCPU, 4GB RAM)

**更便宜的选项**:
- `t3.small` (2 vCPU, 2GB RAM) - 约 $15/月
- 注意: 2GB RAM可能较紧张

**更强大的选项**:
- `t3.large` (2 vCPU, 8GB RAM) - 约 $60/月

### 存储大小

**默认**: 50GB

**根据数据量调整**:
- 小规模: 30GB
- 中等规模: 50GB（推荐）
- 大规模: 100GB+

---

## 📝 配置示例

### 最小配置（terraform.tfvars）

```hcl
# AWS区域
aws_region = "us-east-1"

# 域名配置
domain_name = "cloudlens.songqipeng.com"
route53_zone_name = "songqipeng.com"
create_route53_zone = false  # 如果域名已在Route 53

# SSH密钥
create_key_pair = true
ssh_public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ... your-email@example.com"

# 数据库密码（请修改！）
mysql_password = "YOUR_SECURE_PASSWORD_HERE"
```

---

## ✅ 检查清单

部署前请确认：

- [ ] AWS凭证已配置 (`aws configure`)
- [ ] AWS凭证已验证 (`aws sts get-caller-identity`)
- [ ] SSH公钥已准备好
- [ ] 数据库密码已准备好（强密码）
- [ ] 域名信息已确认（是否在Route 53）
- [ ] Terraform已安装 (`terraform version`)
- [ ] 已运行环境设置脚本 (`./scripts/setup-terraform.sh`)

---

## 🚀 快速开始

```bash
# 1. 环境准备
./scripts/setup-terraform.sh

# 2. 配置变量
cd terraform
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars  # 填写上述信息

# 3. 部署
terraform init
terraform plan
terraform apply
```

---

*最后更新: 2026-01-23*
