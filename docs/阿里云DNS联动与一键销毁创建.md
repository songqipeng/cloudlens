# 阿里云 DNS 联动与一键销毁/创建资源

为节省成本，在「不调试、不给客户演示」时可一键销毁所有资源；需要调试或演示时再一键创建并自动把域名解析指到新 IP。

---

## 一、阿里云域名解析需要提供的凭证

域名解析在阿里云时，重建资源后需要**用 API 更新 A 记录**，把子域名（如 `cloudlens`）指到新服务器的公网 IP。

### 1. 需要的凭证

| 凭证 | 说明 | 示例 |
|------|------|------|
| **AccessKey ID** | 阿里云访问密钥 ID | `LTAI5t...` |
| **AccessKey Secret** | 阿里云访问密钥 Secret | `xxx...` |

建议使用 **RAM 子账号** 的 AccessKey，只给「云解析 DNS」最小权限，不要用主账号密钥。

### 2. RAM 子账号权限（推荐）

在 **阿里云控制台 → 访问控制 RAM → 用户** 中：

1. 创建子用户（如 `cloudlens-dns`），并为其创建 **AccessKey**。
2. 为该用户授予 **云解析 DNS** 权限，二选一：
   - **系统策略**：`AliyunDNSFullAccess`（云解析完全管理，简单）
   - **自定义策略**（仅允许改指定域名，更安全）：

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "alidns:DescribeDomainRecords",
        "alidns:DescribeSubDomainRecords",
        "alidns:UpdateDomainRecord"
      ],
      "Resource": [
        "acs:alidns:*:*:domain/你的主域名"
      ]
    }
  ]
}
```

将上面的 `你的主域名` 换成实际主域名（如 `songqipeng.com`）。

### 3. 配置方式

任选一种，供脚本读取：

- **环境变量**（推荐，不落盘）：
  - `ALIYUN_ACCESS_KEY_ID`
  - `ALIYUN_ACCESS_KEY_SECRET`
- **配置文件**：在项目根目录创建 `scripts/.env.aliyun`（不要提交到 Git），内容示例：

```bash
ALIYUN_ACCESS_KEY_ID=LTAI5t...
ALIYUN_ACCESS_KEY_SECRET=xxx...
ALIYUN_DNS_DOMAIN=songqipeng.com
ALIYUN_DNS_RR=cloudlens
```

- 脚本参数：`scripts/aliyun_dns_update.py --domain songqipeng.com --rr cloudlens --ip <新IP>`

### 4. 域名与解析说明

- **主域名**（DomainName）：在阿里云解析里的「域名」，如 `songqipeng.com`。
- **主机记录**（RR）：子域名，如 `cloudlens` 表示 `cloudlens.songqipeng.com`。
- 脚本会查找该域名下 **A 记录** 中 `RR` 对应的记录，并更新为指定 IP（创建资源后的新公网 IP）。

---

## 二、一键销毁 / 一键创建

### 1. 一键销毁（不演示、不调试时用）

```bash
cd /path/to/cloudlens
./scripts/destroy-all.sh
```

- 会执行 `terraform destroy`（当前 Terraform 为 AWS 资源），销毁 EC2 等。
- 销毁后域名解析可保持不动（解析会指向已不存在的 IP），下次创建会更新为新 IP。

### 2. 一键创建（要演示或调试时用）

```bash
cd /path/to/cloudlens
./scripts/create-all.sh
```

- 执行 `terraform apply` 创建 EC2 等资源。
- 从 Terraform 输出中取 **公网 IP**。
- 若配置了阿里云凭证和域名，会调用 `scripts/aliyun_dns_update.py` 更新 `RR` 的 A 记录到该 IP，实现 **销毁后重建并自动联动域名解析**。

### 3. 前置条件

- 已安装并配置 **Terraform**、**AWS CLI**（若使用当前仓库的 AWS Terraform）。
- 一键创建并更新 DNS 时，需按上文配置 **阿里云 AccessKey** 和域名（`ALIYUN_DNS_DOMAIN`、`ALIYUN_DNS_RR` 或脚本参数）。

---

## 三、脚本与文件说明

| 文件 | 作用 |
|------|------|
| `scripts/destroy-all.sh` | 一键销毁所有 Terraform 管理的资源 |
| `scripts/create-all.sh` | 一键创建资源并在创建后更新阿里云 DNS A 记录 |
| `scripts/aliyun_dns_update.py` | 根据新 IP 更新阿里云云解析 A 记录（被 create-all.sh 调用） |
| `scripts/.env.aliyun` | 可选，存放阿里云密钥与域名（勿提交 Git） |

---

## 四、安全注意

- 不要将 `ALIYUN_ACCESS_KEY_SECRET` 或 `.env.aliyun` 提交到 Git；`.gitignore` 中应包含 `scripts/.env.aliyun`。
- 生产环境建议用 RAM 子账号 + 仅「指定域名」的 DNS 权限，避免使用主账号密钥。
