# CloudLens Web 自动化测试

## 概述

本目录包含 CloudLens Web 应用的完整自动化测试脚本，使用 Playwright 进行浏览器自动化测试和视频录制。

## 测试内容

测试覆盖以下功能模块：

1. **首页仪表板** - 主仪表板页面
2. **成本分析** - 成本分析页面，包含成本趋势图
3. **成本趋势** - 成本趋势分析
4. **资源管理** - 云资源管理页面
5. **优化建议** - 成本优化建议
6. **预算管理** - 预算管理页面
7. **折扣分析** - 折扣趋势分析
8. **安全中心** - 安全检查页面
9. **报告生成** - 报告生成页面
10. **设置** - 系统设置页面

## 运行测试

### 前置条件

1. **启动后端服务**：
   ```bash
   cd web/backend
   python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
   ```

2. **启动前端服务**：
   ```bash
   cd web/frontend
   npm run dev
   ```

3. **安装测试依赖**：
   ```bash
   cd web/frontend
   npm install
   npx playwright install chromium
   ```

### 运行测试

#### 方式1：使用测试脚本（推荐）

```bash
cd web/frontend
./tests/run-test.sh
```

#### 方式2：直接使用 Playwright

```bash
cd web/frontend
npx playwright test tests/web-full-test.spec.ts --project=chromium
```

#### 方式3：显示浏览器窗口运行（便于观察）

```bash
cd web/frontend
npx playwright test tests/web-full-test.spec.ts --project=chromium --headed
```

## 测试输出

### 视频文件

测试过程中会自动录制视频，保存在：
- `web/frontend/test-recordings/` 目录

视频文件格式：`.webm`

### 截图文件

每个测试模块的截图保存在：
- `web/frontend/test-recordings/` 目录

截图命名格式：`{模块名}_screenshot.png` 或 `{模块名}_error.png`

### 测试报告

HTML 测试报告保存在：
- `web/frontend/playwright-report/index.html`

查看报告：
```bash
cd web/frontend
npx playwright show-report
```

## 测试配置

测试配置在 `playwright.config.ts` 中，主要配置项：

- **超时时间**：5分钟
- **浏览器**：Chrome
- **视口大小**：1920x1080
- **视频录制**：启用
- **截图**：失败时自动截图

## 测试结果解读

- ✅ **成功**：页面正常加载，无关键错误
- ❌ **失败**：页面加载失败或包含关键错误信息
- ⏭️ **跳过**：测试被跳过

## 故障排查

### 测试失败

1. **检查服务是否运行**：
   - 后端：`curl http://localhost:8000/health`
   - 前端：`curl http://localhost:3000`

2. **查看错误截图**：
   - 检查 `test-recordings/` 目录中的 `*_error.png` 文件

3. **查看测试日志**：
   - 运行测试时会输出详细日志

### 视频未生成

1. **检查 Playwright 安装**：
   ```bash
   npx playwright install chromium
   ```

2. **检查权限**：
   - 确保 `test-recordings/` 目录有写权限

3. **检查磁盘空间**：
   - 视频文件可能较大，确保有足够空间

## 注意事项

1. **测试时间**：完整测试大约需要 2-3 分钟
2. **资源消耗**：测试会启动 Chrome 浏览器，消耗一定系统资源
3. **网络要求**：需要后端和前端服务正常运行
4. **数据依赖**：某些测试可能需要特定的测试数据

## 自定义测试

可以修改 `web-full-test.spec.ts` 来：

- 添加新的测试模块
- 修改测试超时时间
- 调整等待时间
- 添加自定义交互操作

## 相关文件

- `web-full-test.spec.ts` - 主测试脚本
- `playwright.config.ts` - Playwright 配置
- `run-test.sh` - 测试运行脚本

