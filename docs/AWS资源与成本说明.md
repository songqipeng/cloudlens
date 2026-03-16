# AWS 资源使用与成本说明

**说明**：**香港区（ap-east-1）已重新部署**；东京区（ap-northeast-1）无资源。  
**Terraform**：`terraform.tfvars` 已设为 `aws_region = "ap-east-1"`，当前由 Terraform 管理香港区资源。

---

## 一、当前资源（香港区 ap-east-1）

| 类型 | 资源 | 说明 |
|------|------|------|
| **EC2** | i-0ccb8911a72f454f2 | t3.medium，公网 **18.167.167.25** |
| **ALB** | cloudlens-alb-v2 | **cloudlens-alb-v2-554727073.ap-east-1.elb.amazonaws.com** |
| **域名** | cloudlens.songqipeng.com | 需解析到上述 ALB DNS（CNAME 或 A 记录指向 ALB） |
| **SSH** | `ssh -i ~/.ssh/cloudlens-key ec2-user@18.167.167.25` | 或 `~/.ssh/config` 中 Host `cloudlens-aws` 指向该 IP |
| **HTTPS** | 已配置 | ALB 443 已挂 ACM 证书，HTTP 自动跳 HTTPS。默认管理员见 `docs/默认管理员与重置密码.md` |

删除脚本：单区域 `scripts/aws-delete-all-hongkong.sh`；全区域 `scripts/aws-delete-all-regions.sh`（可加 `--dry-run` 预览）。

---

## 二、2 月至今成本拆分（预估，账户整体）

Cost Explorer 按账户汇总，**香港 + 东京两套会一起计费**；若只保留一套，可约省一半。

| 服务 | 金额 (USD) | 说明 |
|------|------------|------|
| EC2 - Compute | 18.17 | t3.medium 按需 |
| EC2 - Other | 4.04 | 含 EBS（30+50 GB gp3）等 |
| Elastic Load Balancing | 11.55 | ALB + LCU/流量 |
| Amazon VPC | 6.04 | 可能含数据传出等 |
| Route 53 | 0.50 | 托管区/查询 |
| S3 | ~0 | 可忽略 |
| **合计** | **约 40.30** | 约 11 天，折合月约 **~110 USD** |

---

## 三、可采取的处理与优化

### 1. 降低成本（在可接受前提下）

- **实例规格**  
  - 当前：t3.medium。  
  - 若负载不高，可在 `terraform.tfvars` 中改为 `instance_type = "t3.small"`，再 `terraform apply`（会替换实例，需接受短暂中断）。  
  - 约可省一半 EC2 Compute（t3.small 约一半价格）。

- **数据盘**  
  - 当前：50 GB gp3。若 50GB 富余，可在 `terraform.tfvars` 中调小 `ebs_volume_size`（如 30），再 apply（需先备份/迁移数据再改）。

- **ALB**  
  - 当前：ALB 是主要成本之一。若仅为自用/演示，可考虑改为单机直连（不用 ALB）：实例公网 IP + 域名解析到该 IP，用 Nginx 做 HTTPS（需在实例上配置证书）。  
  - 这会涉及架构调整（去掉 ALB/目标组等），需改 Terraform 并可能影响高可用。

- **Route 53**  
  - 若域名解析已在阿里云，可不在 Route 53 创建托管区（`create_route53_zone = false` 且不引用 Route 53），避免托管区月费。

### 2. 运维与访问

- **SSH 连不上**  
  - 原因已确认：服务端报 `banner line contains invalid characters`，与本机 SSH 客户端版本/实现有关，不是 key 错误。  
  - **推荐**：用 SSM 进实例，不依赖 SSH：
    ```bash
    aws ssm start-session --target i-0af2e2ce16237e972 --region ap-northeast-1
    ```
  - 若必须用 SSH：换一台机器（如 Linux）或本机安装 Homebrew OpenSSH 再试。

- **日常查看资源与费用**  
  - 资源：`aws ec2 describe-instances --region ap-northeast-1` 等（或控制台）。  
  - 费用：控制台 → Cost Explorer，或：
    ```bash
    aws ce get-cost-and-usage --time-period Start=2026-02-01,End=2026-02-12 --granularity MONTHLY --metrics BlendedCost --region us-east-1
    ```

### 3. 区域与 Terraform

- **当前**：仅香港区有 CloudLens 资源，东京区已全部销毁。域名 `cloudlens.songqipeng.com` 已解析到香港 ALB，无需改动。
- **若要用 Terraform 管理香港**：将 `terraform.tfvars` 中 `aws_region` 改为 `ap-east-1`，再 `terraform plan` / `apply`（需先 import 香港现有资源，或在新 state 下按需创建，避免重复建资源）。

### 4. 清理未用资源（当前账户内）

- 同一账户下其他区域若有未使用的实例、卷、弹性 IP、负载均衡等，可在对应区域用控制台或 CLI 检查并删除，避免产生额外费用。

---

## 四、常用命令速查（仅香港）

```bash
# 香港区实例
aws ec2 describe-instances --region ap-east-1 --query 'Reservations[*].Instances[*].[InstanceId,State.Name,PublicIpAddress]' --output table
# SSM 登录
aws ssm start-session --target i-093e75d2cc47bdc7f --region ap-east-1
# 本月成本（需在 us-east-1 调 CE）
aws ce get-cost-and-usage --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) --granularity MONTHLY --metrics BlendedCost --region us-east-1
```

---

以上为当前 AWS 资源使用与成本情况，以及可选的优化与处理方式；按需选用即可。
