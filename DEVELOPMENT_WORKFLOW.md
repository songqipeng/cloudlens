# CloudLens 开发工作流程指南

## 🎯 核心目标
确保始终有一个可用的版本，避免"开发了很多功能却全部不可用"的情况。

---

## 📋 日常开发流程

### 1️⃣ 开始新功能前的准备

```bash
# 确保在主分支
cd /Users/mac/cloudlens
git checkout main
git pull origin main

# 创建新的功能分支（以日期命名，方便识别）
git checkout -b dev/$(date +%Y%m%d)-feature-name

# 例如：git checkout -b dev/20260114-budget-alerts
```

### 2️⃣ 开发单个功能

**重要原则：一次只开发一个小功能**

```bash
# 1. 让AI开发一个功能（例如：添加预算告警）
# 2. 在本地测试（Web + CLI都要测试）
# 3. 测试通过后立即提交

git add .
git commit -m "feat: 添加预算告警功能

- 实现预算阈值设置
- 添加邮件通知
- 测试通过：Web界面正常，CLI命令可用"
```

### 3️⃣ 功能验证检查清单

**每次提交前必须确认：**

- [ ] **前端可以启动**：`cd web/frontend && npm run dev`
- [ ] **后端可以启动**：`cd web/backend && python3 -m uvicorn main:app --reload`
- [ ] **关键API正常**：访问 http://localhost:3000 检查主要功能
- [ ] **CLI命令可用**：`cloudlens --help`
- [ ] **没有明显报错**：检查终端日志

### 4️⃣ 推送到远程

```bash
# 推送到GitHub（建议每天至少一次）
git push origin dev/20260114-budget-alerts
```

---

## 🚨 当开发出问题时的救援方案

### 方案1：快速回滚到上一次提交

```bash
# 查看最近的提交记录
git log --oneline -5

# 回滚到上一个可用的提交（不删除代码，只是撤销提交）
git reset --soft HEAD~1

# 或者直接丢弃所有修改，回到上次提交状态
git reset --hard HEAD~1
```

### 方案2：回滚到某个特定日期的版本

```bash
# 查看某天的提交
git log --since="2026-01-10" --until="2026-01-14" --oneline

# 回滚到特定提交（复制commit的hash）
git reset --hard abc1234

# 例如：git reset --hard ac9fe50
```

### 方案3：创建"救命分支"保存当前状态

```bash
# 如果不确定是否要回滚，先保存当前状态
git branch backup/broken-state-$(date +%Y%m%d)
git push origin backup/broken-state-$(date +%Y%m%d)

# 然后再回滚到可用版本
git reset --hard <可用的commit>
```

---

## 🏷️ 标记稳定版本

### 每周或每完成重要功能后打标签

```bash
# 测试完全通过后，打一个标签
git tag -a v0.6.0-stable -m "Week 6 完成，所有功能测试通过"
git push origin v0.6.0-stable

# 以后可以随时回到这个版本
git checkout v0.6.0-stable
```

**建议的标签命名**：
- `v0.6.0-stable` - 第6周稳定版
- `v0.6.1-hotfix` - 紧急修复版本
- `v0.7.0-beta` - 第7周测试版

---

## 🔄 推荐的每日工作流

```
早上：
├─ git checkout main
├─ git pull origin main
├─ git checkout -b dev/20260114-new-feature
└─ 确认前端、后端都能启动

上午开发：
├─ 开发小功能1 (30-60分钟)
├─ 测试 ✓
├─ git commit -m "feat: 功能1"
├─ 开发小功能2 (30-60分钟)
├─ 测试 ✓
└─ git commit -m "feat: 功能2"

下午开发：
├─ 开发小功能3
├─ 测试 ✓
└─ git commit -m "feat: 功能3"

晚上收尾：
├─ 完整测试所有新功能
├─ git push origin dev/20260114-new-feature
└─ (可选) 合并到main: git checkout main && git merge dev/20260114-new-feature
```

---

## 🧪 自动化测试脚本

### 创建快速健康检查脚本

保存为 `~/cloudlens-health-check.sh`：

```bash
#!/bin/bash

echo "🔍 CloudLens 健康检查"
echo "====================="

# 1. 检查前端
echo -n "前端启动测试... "
cd /Users/mac/cloudlens/web/frontend
timeout 5 npm run dev > /dev/null 2>&1 &
PID=$!
sleep 3
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ 通过"
else
    echo "❌ 失败"
fi
kill $PID 2>/dev/null

# 2. 检查后端
echo -n "后端API测试... "
if curl -s http://127.0.0.1:8000/health | grep -q "healthy"; then
    echo "✅ 通过"
else
    echo "❌ 失败"
fi

# 3. 检查关键API
echo -n "关键API测试... "
if curl -s "http://127.0.0.1:8000/api/accounts" | grep -q "success"; then
    echo "✅ 通过"
else
    echo "❌ 失败"
fi

echo ""
echo "检查完成！"
```

**使用方法**：
```bash
chmod +x ~/cloudlens-health-check.sh
~/cloudlens-health-check.sh
```

---

## 📝 Git提交消息规范

使用清晰的提交消息，方便以后查找可用版本：

```bash
# 好的提交消息 ✅
git commit -m "feat: 添加预算告警功能 - 已测试通过"
git commit -m "fix: 修复MySQL连接池autocommit冲突 - 后端正常启动"
git commit -m "test: 添加前端自动化测试 - 11个测试全部通过"

# 不好的提交消息 ❌
git commit -m "update"
git commit -m "fix bug"
git commit -m "WIP"
```

**提交前缀说明**：
- `feat:` - 新功能
- `fix:` - 修复bug
- `refactor:` - 重构代码
- `test:` - 添加测试
- `docs:` - 文档更新
- `chore:` - 杂项（依赖更新等）

---

## 🛡️ 保护主分支

### 设置规则（在GitHub上）

1. 进入仓库 Settings → Branches
2. 添加规则保护 `main` 分支：
   - ✅ Require pull request reviews before merging
   - ✅ Require status checks to pass before merging

这样可以避免直接把坏代码推到main分支。

---

## 💡 与AI协作的最佳实践

### 1. 明确告诉AI你的工作流程

```
"我要开发一个新功能，请一步一步来：
1. 先实现核心逻辑
2. 我会测试
3. 测试通过后再继续下一步
4. 不要一次性给我完整的实现"
```

### 2. 每次让AI修改代码后立即测试

```
"刚才修改了database.py，请帮我验证：
1. 后端能否正常启动
2. 是否有语法错误
3. MySQL连接是否正常"
```

### 3. 要求AI生成测试命令

```
"请给我测试这个功能的curl命令"
"如何快速验证前端是否正常工作？"
```

---

## 📊 版本管理可视化

### 查看当前状态

```bash
# 查看当前分支和状态
git status
git branch -a

# 查看最近的提交（带时间）
git log --oneline --graph --decorate --date=relative -10

# 查看所有标签（稳定版本）
git tag -l
```

### 快速切换到稳定版本

```bash
# 列出所有稳定版本
git tag -l "*-stable"

# 切换到最近的稳定版本
git checkout v0.6.0-stable
```

---

## 🎯 总结：你的新工作流程

1. **每天开始**：创建新的dev分支
2. **小步开发**：每个功能30-60分钟，不超过2个功能一起开发
3. **立即测试**：功能完成立即测试（前端+后端+API）
4. **快速提交**：测试通过立即commit
5. **每日推送**：每天晚上push到GitHub
6. **周末打标签**：测试充分后打stable标签

**记住口诀**：
```
写一点 → 测一点 → 提交一点 → 推送一点
```

这样即使某次开发失败了，你也可以轻松回到上一个可用的版本！
