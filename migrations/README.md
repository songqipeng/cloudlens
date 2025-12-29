# 数据库迁移脚本

本目录包含CloudLens数据库的迁移脚本。

## 使用方法

### 执行迁移

```bash
# 查看当前数据库版本
./migrate.py status

# 执行所有待执行的迁移
./migrate.py upgrade

# 执行到指定版本
./migrate.py upgrade --target 002

# 回滚到指定版本
./migrate.py downgrade --target 001
```

## 迁移文件命名规范

```
{version}_{description}.sql
```

例如：
- `001_remove_budget_records.sql` - 删除废弃的budget_records表
- `002_add_performance_indexes.sql` - 添加性能索引

## 迁移版本

| 版本 | 描述 | 状态 |
|------|------|------|
| 001 | 删除废弃的budget_records表 | Pending |

## 注意事项

1. **备份优先**: 执行迁移前请先备份数据库
2. **测试环境**: 先在测试环境验证迁移脚本
3. **版本管理**: 迁移版本号必须递增且唯一
4. **回滚脚本**: 每个UP迁移都应提供对应的DOWN回滚脚本
