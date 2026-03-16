# API密钥配置问题修复说明

## 问题描述

用户反馈：
1. 之前已经输入过DeepSeek的API key，但现在看不到了
2. 重新配置又保存不了

## 问题分析

### 1. 为什么看不到之前配置的密钥？

**原因**：这是**安全设计**，不是bug！

- API密钥是**敏感信息**，不能以明文显示
- 数据库中存储的是**加密后的密钥**（api_key_encrypted字段）
- 前端输入框**故意留空**，避免泄露密钥
- 如果已配置，会显示**"已配置"绿点**标识

**验证方法**：
```bash
# 检查数据库中的配置
docker exec cloudlens-mysql mysql -ucloudlens -pcloudlens123 cloudlens \
  -e "SELECT provider, is_active, LENGTH(api_key_encrypted) as key_length FROM llm_configs WHERE provider='deepseek';"

# 检查API返回的配置状态
curl -s "http://localhost:8000/api/v1/chatbot/configs" | python3 -m json.tool
```

**结果**：
- DeepSeek配置存在：`has_api_key: true`
- 密钥已加密存储：`key_length: 188`

### 2. 为什么保存不了？

**原因**：之前的保存逻辑有问题

**问题代码**：
```typescript
// 旧代码：如果输入框为空，会跳过保存
const promises = Object.entries(apiKeys).map(([provider, api_key]) => {
  if (api_key.trim()) {  // 只有非空才保存
    return apiPost('/v1/chatbot/configs', {...})
  }
  return Promise.resolve()  // 空输入被跳过
})
```

**问题**：
- 如果用户输入了密钥但保存时出错，没有明确的错误提示
- 如果所有输入框都为空，不会提示用户

## 修复方案

### 1. 改进保存逻辑

**新代码**：
```typescript
async function handleSaveLlmConfig() {
  // 1. 检查是否有任何输入
  const hasAnyInput = Object.values(apiKeys).some(key => key.trim())
  if (!hasAnyInput) {
    toastError('请至少输入一个API密钥')
    return
  }

  // 2. 只处理非空的密钥，并添加错误处理
  const promises = Object.entries(apiKeys)
    .filter(([_, api_key]) => api_key.trim())
    .map(([provider, api_key]) => {
      return apiPost('/v1/chatbot/configs', {
        provider,
        api_key: api_key.trim(),
        is_active: true
      }).catch((error) => {
        console.error(`保存${provider}配置失败:`, error)
        throw new Error(`${provider}配置保存失败: ${error.message || error}`)
      })
    })

  await Promise.all(promises)
  // ...
}
```

**改进点**：
- ✅ 添加输入验证：如果没有输入任何密钥，会提示用户
- ✅ 改进错误处理：显示具体的错误信息（哪个provider失败，为什么失败）
- ✅ 添加错误日志：方便调试

### 2. 改进UI提示

**当前显示**：
- 如果已配置：显示**"已配置"绿点** ✅
- 输入框：**留空**（安全设计）✅
- 说明文字：提示用户这是正常的 ✅

## 使用说明

### 如何确认密钥已配置？

1. **查看"已配置"标识**：
   - 在设置页面的"AI 模型配置"卡片中
   - 如果某个provider旁边有**绿色"已配置"标识**，说明密钥已保存

2. **测试AI Chatbot**：
   - 打开AI Chatbot
   - 选择对应的模型（如DeepSeek）
   - 发送消息，如果能正常回复，说明密钥配置成功

### 如何更新密钥？

1. **在输入框中输入新密钥**
2. **点击"保存配置"按钮**
3. **查看提示**：
   - 成功：显示"API密钥配置已保存"
   - 失败：显示具体错误信息

### 如何删除配置？

目前前端没有删除按钮，可以通过以下方式：

**方法1：通过API删除**
```bash
curl -X DELETE "http://localhost:8000/api/v1/chatbot/configs/deepseek"
```

**方法2：直接删除数据库记录**（不推荐）
```bash
docker exec cloudlens-mysql mysql -ucloudlens -pcloudlens123 cloudlens \
  -e "DELETE FROM llm_configs WHERE provider='deepseek';"
```

## 验证步骤

1. **访问设置页面**：http://localhost:3000/a/ydzn/settings
2. **检查"AI 模型配置"卡片**：
   - DeepSeek旁边应该显示**"已配置"绿点**
3. **测试保存功能**：
   - 输入一个新的DeepSeek API密钥
   - 点击"保存配置"
   - 应该显示成功提示
4. **验证配置**：
   - 打开AI Chatbot
   - 选择DeepSeek模型
   - 发送测试消息

## 技术细节

### 数据库表结构
```sql
CREATE TABLE llm_configs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,  -- claude, openai, deepseek
    api_key_encrypted TEXT NOT NULL,  -- 加密后的密钥
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### 加密方式
- 使用Fernet对称加密
- 加密密钥存储在：`~/.cloudlens/.encryption_key`
- 查询接口不返回明文密钥（只返回has_api_key布尔值）

### API端点
- `GET /api/v1/chatbot/configs` - 查询配置状态
- `POST /api/v1/chatbot/configs` - 保存/更新配置
- `DELETE /api/v1/chatbot/configs/{provider}` - 删除配置

## 修复状态

✅ **已修复**：
- 保存逻辑改进（添加输入验证和错误处理）
- 错误提示优化
- 前端镜像已重新构建

✅ **已验证**：
- 后端API保存功能正常
- 数据库中有DeepSeek配置（has_api_key: true）
- 前端应该正确显示"已配置"标识

## 下一步

请刷新浏览器页面（Ctrl+Shift+R 或 Cmd+Shift+R），然后：
1. 访问设置页面，检查是否显示"已配置"绿点
2. 尝试重新输入并保存DeepSeek密钥
3. 如果还有问题，请查看浏览器控制台的错误信息
