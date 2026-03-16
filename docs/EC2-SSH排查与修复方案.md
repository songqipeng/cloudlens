# 香港 EC2 SSH 无法连接 — 排查结果与修复方案

**实例**: i-093e75d2cc47bdc7f（95.40.35.172）  
**区域**: ap-east-1（香港）  
**AMI**: al2023-ami-**minimal**（AL2023 最小化版）

---

## 一、已完成的排查（通过 AWS 命令行）

### 1. IAM
- 东京 `terraform destroy` 时已删除角色 `cloudlens-ec2-role-v2` 和实例 profile，香港实例之前挂的是已删除的 profile。
- **已做**：用 AWS CLI 重新创建了 `cloudlens-ec2-role-v2` 和 `cloudlens-ec2-profile-v2`，并附加 **AmazonSSMManagedInstanceCore**，且已用 `replace-iam-instance-profile-association` 把香港实例关联到新 profile。

### 2. SSM（Systems Manager）
- 已重启实例以使新 IAM 生效。
- **结果**：`describe-instance-information` 在 ap-east-1 始终为空，实例未出现在 SSM 托管列表。
- **原因推断**：当前 AMI 为 **AL2023 minimal**，很可能未预装或未启用 SSM 代理，因此无法通过 SSM 进实例修 sshd。

### 3. 控制台输出
- 已用 `get-console-output` 查看，仅见内核/网络等日志，未见 cloud-init 或 sshd 相关报错。

### 4. EC2 Instance Connect
- `send-ssh-public-key` 成功，临时公钥已推送到实例。
- 用同一临时私钥 SSH 到 95.40.35.172 仍被关闭，说明**问题不在 key**，而在 SSH 协议阶段（banner/版本协商）。

### 5. 串行控制台
- 已为 ap-east-1 执行 `enable-serial-console-access`。
- `send-serial-console-ssh-public-key` 成功，但用本机 `ssh` 连 `ec2-serial-console.ap-east-1.api.aws` 时同样在 22 端口被关闭（可能是本机 SSH 客户端与 AWS 串行控制台网关的兼容性）。
- 当前报错 **SerialConsoleSessionLimitExceeded**：已有 1 个串行控制台会话占用，需等该会话断开约 30 秒后再推 key，或从浏览器在控制台里「EC2 Serial Console → Connect」尝试。

### 6. 结论（根因）
- 服务端 sshd 日志（此前在东京实例上已确认）为：**`banner line contains invalid characters`**。
- 即：**AL2023 上的 sshd 认为本机 SSH 客户端发来的版本行（banner）含非法字符**，在协商前就断开连接。
- Key 正确、网络可达、安全组 22 开放；问题在**客户端发来的首行**与**服务端严格校验**不兼容。

---

## 二、修复思路（最终仍希望通过 SSH 连上）

### 方案 A：在实例内改 sshd（需先有 shell）

- 若能通过 **SSM** 或 **串行控制台** 进系统，可在实例内：
  - 查看 `/var/log/secure` 或 `journalctl -u sshd` 确认当前报错；
  - 检查 `/etc/ssh/sshd_config` 与 `/etc/ssh/sshd_config.d/`，看是否有可放宽的配置（OpenSSH 官方可能无“放宽 banner”选项，但可确认是否有自定义限制）；
  - 若有需要，可考虑在测试后替换或包装 sshd（需谨慎，并备份）。
- **当前阻碍**：SSM 未就绪（minimal AMI），串行控制台需从浏览器或等会话释放后再试。

### 方案 B：换用能连上的 SSH 客户端（推荐先做）

- 本机（Mac）换一个 SSH 实现，避免当前系统自带的 OpenSSH + LibreSSL 发出的 banner 被拒：
  - 安装 Homebrew OpenSSH，用其 `ssh` 连：
    ```bash
    brew install openssh
    /opt/homebrew/bin/ssh -i ~/.ssh/cloudlens-key -o StrictHostKeyChecking=no ec2-user@95.40.35.172
    ```
  - 或用 **Qoder IDE 的 Remote-SSH** 再试一次（若之前能连上，说明其内置/使用的 SSH 客户端可能兼容）。

### 方案 C：以后新实例改用「非 minimal」AMI + SSM

- 若以后用 Terraform/控制台再建实例，建议：
  - 使用 **AL2023 标准版**（或 AL2）AMI，而不是 **minimal**，以便预装并启用 SSM 代理。
  - 保留 IAM 角色与 `AmazonSSMManagedInstanceCore`，这样下次可直接用 SSM 进实例排查或修 sshd，不依赖 22 端口。

### 方案 D：从浏览器用串行控制台（可立刻试）

- 在 AWS 控制台 → EC2 → 选择实例 i-093e75d2cc47bdc7f → **Actions** → **Monitor and troubleshoot** → **EC2 Serial Console** → **Connect**。
- 若浏览器内终端能连上，可在实例内直接改 sshd 配置、重启 sshd，再试本机 SSH。
- 若提示已有会话，可等约 30 秒或 1 小时后重试；或从同一控制台页面查看是否有“断开”选项。

---

## 三、当前可直接用的命令（key 与 IP 已确认）

```bash
# 本机 SSH（若换用 Homebrew openssh 或 Qoder 可能成功）
ssh -i ~/.ssh/cloudlens-key -o StrictHostKeyChecking=no ec2-user@95.40.35.172

# 使用 config
ssh -F ~/.ssh/config_cloudlens cloudlens-aws
```

**config_cloudlens** 已指向香港 IP：95.40.35.172，IdentityFile 为 `~/.ssh/cloudlens-key`。

---

## 四、小结

- 已通过 AWS 命令行确认：IAM 已恢复并挂到香港实例、EC2 Instance Connect 与串行控制台 API 可用、问题集中在 **sshd 对客户端 banner 的校验**。
- 当前无法在实例内改 sshd，是因为 SSM 未注册（minimal AMI），串行控制台需从浏览器或等会话释放后再用。
- **建议优先**：本机用 **Homebrew OpenSSH** 或 **Qoder Remote-SSH** 再试；同时可在控制台用 **EC2 Serial Console（浏览器）** 登录一次，若成功则在实例内修 sshd，使本机系统自带 `ssh` 也能连上。

---

## 五、Qoder 为何能连 — 排查结论

在不对 Qoder 做逆向的前提下，已做如下确认：

1. **Qoder 用的仍是系统 SSH**
   - 扩展为 **Open Remote - SSH**（publisher: aicoding），实现 `onResolveRemoteAuthority:ssh-remote`。
   - 扩展内仅有 askpass 脚本（用于本机弹窗要密码），**没有**自带 SSH 二进制或 Node 版 SSH 库；实际建连由 VS Code 系主进程按 PATH 调用本机 `ssh`。
   - 因此若 Qoder 和终端用同一台 Mac、同一 PATH，理论上会用到同一个 `ssh`，都应被当前香港实例的 sshd 以「banner invalid」关掉。

2. **Qoder 仍可能“能连”的几种情况**
   - **连的不是当前香港实例**：例如之前连的是东京实例（不同 AMI/sshd），东京 destroy 后未再对香港 95.40.35.172 用 Qoder 试过。
   - **走 Qoder 云端隧道**：若 Qoder 把 Remote-SSH 流量经 `center.qoder.sh` 等后端转发，真正执行 SSH 的可能是他们机房里的 Linux，发出的客户端版本行与 Mac 不同，有可能被 AL2023 接受；扩展代码已压缩，未在本地找到明确证据，仅作合理推测。
   - **环境不一致**：Qoder 从 Dock 启动时 PATH 通常只有 `/usr/bin`，即 `/usr/bin/ssh`；若你曾从终端用 `open -a Qoder` 启动，或曾改过 Qoder 的 `remote.SSH.path`，则可能用到了别的 `ssh`。

3. **建议验证方式（不登 AWS 控制台）**
   - 在同一台 Mac 上：用 Qoder 的 Remote-SSH 连接 **当前香港主机**（95.40.35.172 或 `~/.ssh/config` 里对应 Host），看是否仍能连上。
   - 若 Qoder 能连而终端不能：在连接过程中在终端执行 `ps aux | grep ssh`，看 Qoder 起的进程里用的是哪条 `ssh`（例如 `/usr/bin/ssh` 还是 `/opt/homebrew/bin/ssh`），便于对比复现。
   - 若 Qoder 也连不上当前香港实例：则与“东京能连、香港不能”一致，根因就是当前实例的 sshd banner 校验，需在实例内改 sshd 或换用能通过校验的客户端/环境。

---

## 六、不登录 AWS 控制台时的可操作办法

在无法用 SSM、且不想打开 AWS 网页的前提下，可选只有：

1. **串行控制台（仍须在浏览器里点一次）**
   - 唯一“从零进系统”的方式：在 AWS 控制台 → EC2 → 该实例 → **Monitor and troubleshoot** → **EC2 Serial Console** → **Connect**。浏览器里会开一个终端，连上后可在实例内改 sshd、重启服务，之后本机 `ssh` 才有机会连上。
   - 若提示 **SerialConsoleSessionLimitExceeded**：说明已有会话占用，等约 30 秒～数分钟再试，或从同一页面看是否有断开入口。

2. **今后新建实例时避免再踩坑**
   - 用 **AL2023 标准版**（或 AL2）AMI，不用 minimal，并保留 IAM + **AmazonSSMManagedInstanceCore**，以后可直接用 CLI：`aws ssm start-session --target <instance-id> --region ap-east-1` 进实例，无需 22 端口、无需打开控制台页面。
