# 权限检查清单

## 当前问题总结

### 1. ✅ 已修复：资源查询只查询配置的 region
- **问题**: `list_resources` API 只查询配置的 region（cn-hangzhou），但实际资源在 cn-beijing（378个）和 cn-shanghai（1个）
- **修复**: 修改 `list_resources` API，让 ECS 查询所有区域
- **状态**: ✅ 已修复

### 2. ⚠️ 需要检查：数据获取权限

根据测试结果，以下功能可能需要特定权限：

#### 账单数据（Billing）
- **API**: `/api/billing/overview`
- **需要权限**: 
  - 阿里云 BSS（Business Support System）API 权限
  - `bssapi:QueryInstanceBill` 权限
  - 或者需要导入账单 CSV 文件到数据库

#### 折扣分析（Discounts）
- **API**: `/api/discounts/trend`
- **需要权限**:
  - 账单数据访问权限
  - 或者需要导入历史账单 CSV 文件

#### 安全合规（Security）
- **API**: `/api/security/overview`
- **需要权限**:
  - ECS 实例查询权限
  - 安全组查询权限
  - 磁盘查询权限

#### 优化建议（Optimization）
- **API**: `/api/optimization/suggestions`
- **需要权限**:
  - 资源查询权限
  - 成本数据访问权限

## 需要您提供的权限信息

请检查以下权限是否已配置：

### 1. 阿里云 RAM 权限
请确认您的 AccessKey 是否有以下权限：

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeRegions",
        "ecs:DescribeDisks",
        "ecs:DescribeSecurityGroups",
        "bssapi:QueryInstanceBill",
        "bssapi:QueryBill",
        "bssapi:QueryAccountBill"
      ],
      "Resource": "*"
    }
  ]
}
```

### 2. 账单数据
- **选项 A**: 使用 BSS API 实时查询（需要 `bssapi:QueryInstanceBill` 权限）
- **选项 B**: 导入历史账单 CSV 文件到数据库

### 3. 数据库权限
- MySQL 数据库连接权限
- 读写权限（用于缓存和账单数据存储）

## 测试建议

1. **测试资源查询**:
   ```bash
   curl "http://127.0.0.1:8000/api/resources?account=ydzn&type=ecs&force_refresh=true"
   ```
   应该返回 379 个实例（378 + 1）

2. **测试账单数据**:
   ```bash
   curl "http://127.0.0.1:8000/api/billing/overview?account=ydzn"
   ```
   如果返回 0，可能需要：
   - 检查 BSS API 权限
   - 或者导入账单 CSV 文件

3. **测试折扣分析**:
   ```bash
   curl "http://127.0.0.1:8000/api/discounts/trend?account=ydzn&months=6"
   ```
   需要账单数据支持

## 下一步

请告诉我：
1. ✅ 资源查询是否正常（应该显示 379 个实例）
2. ⚠️ 账单数据是否需要导入 CSV 文件，还是使用 BSS API？
3. ⚠️ 是否有 BSS API 权限？
4. ⚠️ 是否需要我帮您配置账单数据导入功能？



