# SSH连接问题诊断报告

## 问题现象
- **SSH连接失败**：`Connection closed by 54.248.170.40 port 22`
- **连接阶段**：在密钥交换（kex_exchange_identification）阶段被关闭
- **端口状态**：22端口已开放（nc测试成功）
- **密钥配置**：SSH公钥已正确添加到 `authorized_keys`

## 诊断结果

### ✅ 正常项
1. **安全组规则**：22端口已开放给 `0.0.0.0/0`
2. **网络ACL**：没有阻止22端口的规则
3. **端口可达性**：`nc -zv` 测试显示端口22可达
4. **SSH密钥**：公钥已正确配置到实例的 `authorized_keys`

### ❌ 问题项
1. **user-data脚本执行失败**：
   - cloud-init在运行user-data脚本时因curl包冲突而失败
   - 错误：`Failed to run module scripts-user`
   - 虽然添加了 `--skip-broken`，但脚本执行仍然失败

2. **SSH服务状态未知**：
   - 无法通过SSH连接检查SSH服务状态
   - 无法通过SSM（Session Manager插件未安装）检查

3. **连接在密钥交换阶段关闭**：
   - 可能原因：
     - SSH服务配置问题（MaxStartups限制）
     - SSH服务未完全启动
     - 系统资源限制

## 解决方案

### 方案1：重新创建实例（推荐）
使用修复后的 `user-data.sh` 脚本重新创建实例：

```bash
cd terraform
terraform taint aws_instance.cloudlens  # 标记实例需要重新创建
terraform apply  # 重新创建实例
```

**修复内容**：
- 在脚本开始处确保SSH服务启动
- 在脚本结束处再次检查并重启SSH服务
- 改进了错误处理，确保即使部分步骤失败，SSH服务也能正常启动

### 方案2：等待并重试
SSH服务可能需要更多时间完全启动。等待5-10分钟后重试：

```bash
ssh -i ~/.ssh/cloudlens-key ec2-user@54.248.170.40
```

### 方案3：通过AWS控制台检查
1. 登录AWS控制台
2. 进入EC2控制台
3. 选择实例 `i-0ee12b47cdb5ca60d`
4. 点击"连接" → "EC2 Instance Connect" 或 "Session Manager"
5. 检查SSH服务状态：`systemctl status sshd`

## 已修复的user-data.sh
- ✅ 在脚本开始处确保SSH服务启动
- ✅ 在脚本结束处再次检查SSH服务
- ✅ 改进了错误处理逻辑

## 下一步
1. 重新创建实例（推荐）
2. 验证SSH连接
3. 继续部署CloudLens服务
