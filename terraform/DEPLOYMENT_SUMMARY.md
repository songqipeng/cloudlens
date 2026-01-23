# CloudLens AWS部署总结

## ✅ 已完成的工作

### 1. Terraform配置
- ✅ 完整的Terraform配置（main.tf, variables.tf, outputs.tf）
- ✅ 自动创建EC2实例（t3.medium）
- ✅ 自动配置Application Load Balancer
- ✅ 自动申请和配置SSL证书（ACM）
- ✅ 自动配置Route 53 DNS记录
- ✅ 自动配置HTTPS（HTTP自动重定向）
- ✅ 自动部署CloudLens（通过user-data脚本）

### 2. 文档
- ✅ README.md - 完整部署指南
- ✅ QUICK_START.md - 5分钟快速开始
- ✅ DEPLOYMENT_CHECKLIST.md - 部署检查清单
- ✅ REQUIREMENTS.md - 需要提供的信息

### 3. 自动化脚本
- ✅ setup-terraform.sh - 环境设置脚本
- ✅ user-data.sh - EC2实例初始化脚本

---

## 🎯 核心功能

### 自动化部署
1. **EC2实例**: t3.medium (2 vCPU, 4GB RAM)
2. **ALB**: Application Load Balancer（负载均衡）
3. **SSL证书**: 自动申请和验证
4. **DNS**: 自动配置Route 53记录
5. **HTTPS**: 自动配置，HTTP自动重定向到HTTPS
6. **应用部署**: 自动安装Docker、拉取代码、启动服务

### 路由配置
- `/api/*` → 后端服务（端口8000）
- 其他路径 → 前端服务（端口3000）

### 域名支持
- 支持域名已在Route 53（自动查找）
- 支持域名在其他DNS服务商（创建Route 53托管区域）

---

## 📋 需要您提供的信息

### 必需信息
1. **AWS凭证**
   - Access Key ID
   - Secret Access Key
   - 区域（推荐: us-east-1）

2. **域名信息**
   - 域名是否已在Route 53: □ 是  □ 否

3. **SSH公钥**
   - 运行: `cat ~/.ssh/id_rsa.pub`

4. **数据库密码**
   - 强密码（至少16位）

---

## 🚀 部署步骤

### 快速开始（3步）

```bash
# 1. 环境准备
./scripts/setup-terraform.sh

# 2. 配置变量
cd terraform
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars  # 填写配置

# 3. 部署
terraform init
terraform plan
terraform apply
```

**预计时间**: 10-15分钟

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

## 🌐 域名配置

### 情况A: 域名已在Route 53（最简单）

```hcl
create_route53_zone = false
```

✅ **无需任何手动操作**，Terraform自动完成所有配置

### 情况B: 域名在其他DNS服务商

1. 设置 `create_route53_zone = true`
2. 部署后获取名称服务器: `terraform output route53_zone_name_servers`
3. 在DNS服务商配置名称服务器
4. 等待DNS传播（通常几分钟）

---

## ✅ 部署后验证

```bash
# 1. 查看输出
terraform output

# 2. SSH连接
terraform output ssh_command

# 3. 检查服务
ssh -i ~/.ssh/cloudlens-key.pem ec2-user@<ip>
cd /opt/cloudlens/app
docker-compose ps

# 4. 访问
# https://cloudlens.songqipeng.com
```

---

## 📚 文档

- [快速开始](./QUICK_START.md)
- [完整指南](./README.md)
- [检查清单](./DEPLOYMENT_CHECKLIST.md)
- [需要的信息](./REQUIREMENTS.md)

---

*最后更新: 2026-01-23*
