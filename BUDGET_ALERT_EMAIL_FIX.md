# 预算告警邮件发送问题修复报告

## 问题诊断

经过测试，发现以下问题：

### 1. ✅ 已修复：邮件编码问题
**错误信息：**
```
'ascii' codec can't encode characters in position 352-355: ordinal not in range(128)
```

**原因：** 邮件内容包含中文字符，但没有正确指定 UTF-8 编码。

**修复：**
- 使用 `Header` 处理中文主题
- 在 `MIMEText` 中明确指定 `'utf-8'` 编码

### 2. ❌ 需要用户修复：SMTP 密码配置错误

**问题：** 配置文件 `~/.cloudlens/notifications.json` 中的 `smtp_password` 和 `auth_code` 字段包含错误信息字符串，而不是实际的 SMTP 密码。

**当前配置值：**
```json
{
  "smtp_password": "Console Error [API Error] 500 Internal Server Error: ...",
  "auth_code": "Console Error [API Error] 500 Internal Server Error: ..."
}
```

**正确配置应该是：**
```json
{
  "smtp_password": "你的QQ邮箱授权码",
  "auth_code": "你的QQ邮箱授权码"
}
```

## 解决方案

### 步骤 1：获取 QQ 邮箱授权码

1. 登录 QQ 邮箱：https://mail.qq.com
2. 进入"设置" -> "账户"
3. 找到"POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务"
4. 开启"POP3/SMTP服务"或"IMAP/SMTP服务"
5. 点击"生成授权码"
6. 按照提示发送短信，获取授权码（16位字符）

### 步骤 2：更新配置文件

编辑 `~/.cloudlens/notifications.json`：

```json
{
  "email": "5651741@qq.com",
  "smtp_host": "smtp.qq.com",
  "smtp_port": 587,
  "smtp_use_tls": true,
  "smtp_user": "5651741@qq.com",
  "smtp_from": "5651741@qq.com",
  "smtp_password": "你的16位授权码",
  "auth_code": "你的16位授权码",
  "default_receiver_email": "5651741@qq.com"
}
```

**重要：** 将 `"你的16位授权码"` 替换为实际的 QQ 邮箱授权码。

### 步骤 3：测试邮件发送

运行测试脚本：

```bash
python3 test_budget_alert_email.py
```

如果测试成功，会显示：
```
✅ 邮件发送成功！
   请检查邮箱 5651741@qq.com 的收件箱（包括垃圾邮件文件夹）
```

## 已实现的改进

1. ✅ **修复编码问题**：邮件现在可以正确发送包含中文的内容
2. ✅ **添加配置验证**：自动检测密码配置错误
3. ✅ **改进日志记录**：详细的错误信息，便于排查问题
4. ✅ **创建测试脚本**：`test_budget_alert_email.py` 用于测试邮件发送功能

## 测试结果

**当前状态：** ❌ 邮件发送失败

**失败原因：** SMTP 密码配置错误（包含错误信息字符串，不是实际密码）

**修复后预期：** ✅ 邮件发送成功

## 下一步

1. 按照上述步骤更新配置文件中的 SMTP 密码
2. 运行测试脚本验证邮件发送功能
3. 触发预算告警，验证邮件是否正常发送

## 注意事项

- QQ 邮箱授权码是 16 位字符，不是邮箱密码
- 授权码需要妥善保管，不要泄露
- 如果授权码泄露，可以在 QQ 邮箱中重新生成

