# CloudLens 示例文件

本目录包含CloudLens的使用示例代码。

## 示例列表

### 1. 基础使用 (`basic_usage.py`)

演示基本功能：
- 列出ECS实例
- 筛选资源
- 检查闲置资源

运行方式：
```bash
cd examples
python3 basic_usage.py
```

### 2. 高级功能 (`advanced_usage.py`)

演示高级功能：
- Dry-run修复计划
- RAM权限审计
- API操作安全检查
- 创建修复计划

运行方式：
```bash
cd examples
python3 advanced_usage.py
```

## 前置条件

在运行示例前，请确保：

1. 已安装依赖：
```bash
pip install -r requirements.txt
```

2. 已配置云账号：
```bash
python3 main_cli.py config add
```

## 注意事项

- 示例代码仅用于演示，不会进行实际的修改操作
- 部分示例需要真实的云账号凭证
- 建议在测试环境下运行

## 更多信息

查看完整文档：
- [用户手册](../docs/USER_GUIDE.md)
- [技术架构](../TECHNICAL_ARCHITECTURE.md)
- [README](../README.md)
