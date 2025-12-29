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

### 审查流程

1. **提交 PR** - 在 GitHub 上创建 Pull Request
2. **CI 检查** - 等待 CI 自动运行测试和检查
3. **代码审查** - 维护者进行代码审查
4. **修改反馈** - 根据审查意见修改代码
5. **批准合并** - 审查通过后合并到主分支

### 审查标准

PR提交后会进行代码审查，请注意：

1. **CI必须通过** - 所有测试和检查必须绿灯
2. **代码质量** - 遵循规范，逻辑清晰
3. **测试覆盖** - 新代码必须有测试
4. **文档完整** - 功能性变更需更新文档

### 审查检查清单

审查者会检查以下内容：

- [ ] 代码遵循项目规范（Black, Flake8, MyPy）
- [ ] 所有测试通过（pytest）
- [ ] 测试覆盖率达标（新代码 >80%）
- [ ] 代码逻辑清晰，无冗余
- [ ] 添加了必要的注释和文档
- [ ] 提交信息符合规范
- [ ] PR 描述清晰完整
- [ ] 没有引入安全漏洞（bandit）

### PR 模板

创建 PR 时，请使用以下模板：

```markdown
## 变更类型
- [ ] 新功能 (feature)
- [ ] Bug 修复 (fix)
- [ ] 文档更新 (docs)
- [ ] 代码重构 (refactor)
- [ ] 性能优化 (perf)
- [ ] 测试相关 (test)
- [ ] 构建/工具链 (chore)

## 变更描述
<!-- 简要描述本次变更的内容 -->

## 相关 Issue
<!-- 关联的 Issue 编号，如：Closes #123 -->

## 测试说明
<!-- 说明如何测试本次变更 -->

## 检查清单
- [ ] 代码遵循项目规范
- [ ] 添加了必要的测试
- [ ] 所有测试通过
- [ ] 更新了相关文档
- [ ] Commit message 符合规范
```

### 审查反馈处理

收到审查反馈后：

1. **仔细阅读** - 理解审查者的建议
2. **积极沟通** - 如有疑问，在 PR 中回复
3. **及时修改** - 根据反馈修改代码
4. **重新提交** - 修改后重新提交，CI 会自动运行

### 审查时间

- **首次审查**：通常在 1-3 个工作日内完成
- **修改反馈**：根据修改复杂度，1-2 个工作日
- **紧急修复**：可联系维护者加速审查

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

## 📝 PR 模板

创建 Pull Request 时，请使用以下模板：

### 功能 PR

```markdown
## 🎯 功能描述
<!-- 简要描述新功能 -->

## 📝 变更内容
- [ ] 新增功能 A
- [ ] 新增功能 B
- [ ] 更新文档

## 🔗 相关 Issue
Closes #123

## ✅ 测试说明
<!-- 说明如何测试新功能 -->
1. 步骤 1
2. 步骤 2

## 📸 截图（如适用）
<!-- 如果是 UI 变更，请添加截图 -->

## ✅ 检查清单
- [ ] 代码遵循项目规范
- [ ] 添加了必要的测试
- [ ] 所有测试通过
- [ ] 更新了相关文档
- [ ] Commit message 符合规范
```

### Bug 修复 PR

```markdown
## 🐛 Bug 描述
<!-- 描述修复的 Bug -->

## 🔧 修复方案
<!-- 说明如何修复 -->

## 🔗 相关 Issue
Fixes #123

## ✅ 测试说明
<!-- 说明如何验证修复 -->
1. 复现步骤
2. 验证修复

## ✅ 检查清单
- [ ] 添加了回归测试
- [ ] 所有测试通过
- [ ] 更新了相关文档
```

### 文档更新 PR

```markdown
## 📚 文档更新
<!-- 描述文档更新内容 -->

## 📝 变更内容
- [ ] 更新 API 文档
- [ ] 更新用户指南
- [ ] 更新开发文档

## ✅ 检查清单
- [ ] 文档格式正确
- [ ] 链接有效
- [ ] 示例代码可运行
```

## 🙋 获取帮助

- **GitHub Issues**: 提问或讨论
- **邮件**: your-email@example.com
- **文档**: 查看 `docs/` 目录

## 📄 许可证

贡献的代码将遵循项目的MIT许可证。

---

再次感谢您的贡献！🎉
