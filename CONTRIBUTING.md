# 贡献指南

感谢您对CloudLens项目感兴趣！我们欢迎所有形式的贡献。

## 🚀 如何开始

### 1. Fork项目

点击GitHub页面右上角的"Fork"按钮

### 2. Clone到本地

```bash
git clone https://github.com/YOUR_USERNAME/aliyunidle.git
cd aliyunidle
```

### 3. 设置开发环境

```bash
# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 安装开发依赖
pip install pytest pytest-cov black flake8 mypy bandit pre-commit

# 激活pre-commit hooks
pre-commit install
```

## 📝 开发流程

### 1. 创建分支

```bash
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/bug-description
```

### 2. 编写代码

遵循项目的代码规范（见下方）

### 3. 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/core/test_filter_engine.py

# 查看覆盖率
pytest --cov=core --cov=providers --cov-report=html
```

### 4. 代码检查

```bash
# 格式化代码
black .

# 检查代码风格
flake8 .

# 类型检查
mypy core providers

# 安全扫描
bandit -r core providers
```

### 5. 提交代码

```bash
git add .
git commit -m "feat: add new feature description"
git push origin feature/your-feature-name
```

### 6. 创建Pull Request

在GitHub上创建PR，填写详细描述

## 🎨 代码规范

### Python代码风格

- 遵循 **PEP 8** 规范
- 使用 **Black** 格式化（行长度100）
- 使用 **Type Hints** 进行类型标注
- 编写清晰的**Docstrings**

```python
def example_function(param1: str, param2: int) -> bool:
    \"\"\"
    函数功能简短描述

    Args:
        param1: 参数1说明
        param2: 参数2说明

    Returns:
        返回值说明

    Raises:
        ExceptionType: 异常说明
    \"\"\"
    pass
```

### 提交信息规范

使用[Conventional Commits](https://www.conventionalcommits.org/)格式：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type类型**:
- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具链更新

**示例**:
```
feat(provider): add AWS provider support

Implement basic AWS provider functionality including:
- EC2 instance listing
- RDS database listing
- Permission checking

Closes #123
```

## 🧪 测试要求

### 必须编写测试

- 新功能必须包含单元测试
- Bug修复必须包含回归测试
- 测试覆盖率 >80%

### 测试结构

```
tests/
├── core/           # 核心模块测试
│   ├── test_filter_engine.py
│   └── test_idle_detector.py
├── providers/      # Provider测试
│   ├── test_aliyun_provider.py
│   └── test_tencent_provider.py
└── integration/    # 集成测试
```

## 📚 文档要求

### 代码文档

- 所有公共函数/类必须有Docstring
- 复杂逻辑要添加注释
- README.md及时更新

### 文档类型

- **API文档**: 自动从Docstring生成
- **用户手册**: `docs/USER_GUIDE.md`
- **架构文档**: `TECHNICAL_ARCHITECTURE.md`

## 🔍 代码审查

PR提交后会进行代码审查，请注意：

1. **CI必须通过** - 所有测试和检查必须绿灯
2. **代码质量** - 遵循规范，逻辑清晰
3. **测试覆盖** - 新代码必须有测试
4. **文档完整** - 功能性变更需更新文档

## 🐛 提交Issue

### Bug报告

```markdown
**描述**: 简短描述bug
**复现步骤**:
1. 第一步
2. 第二步
**预期行为**: 应该发生什么
**实际行为**: 实际发生了什么
**环境信息**:
- OS: macOS 13.0
- Python: 3.10
- 版本: v1.0.0
```

### 功能请求

```markdown
**功能描述**: 描述新功能
**使用场景**: 什么场景需要这个功能
**实现建议**: （可选）你的实现想法
```

## 📋 开发检查清单

提交PR前，请确认：

- [ ] 代码遵循项目规范
- [ ] 添加了必要的测试
- [ ] 所有测试通过
- [ ] 代码格式化（black）
- [ ] 类型检查通过（mypy）
- [ ] 更新了相关文档
- [ ] Commit message符合规范
- [ ] PR描述清晰完整

## 🙋 获取帮助

- **GitHub Issues**: 提问或讨论
- **邮件**: your-email@example.com
- **文档**: 查看 `docs/` 目录

## 📄 许可证

贡献的代码将遵循项目的MIT许可证。

---

再次感谢您的贡献！🎉
