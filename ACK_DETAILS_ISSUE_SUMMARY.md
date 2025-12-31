# ACK 资源详细信息显示问题总结

## 问题描述

**现象**：前端资源详情页面无法显示 ACK 集群的详细信息（Kubernetes 版本、节点数量、网络配置、插件信息等），只显示基础信息。

**期望**：前端应该显示 4 个信息卡片：
1. Kubernetes 信息（版本、节点数、集群类型等）
2. 网络配置（VPC、VSwitch、安全组、Service CIDR 等）
3. 插件信息（所有已安装的插件列表）
4. 其他信息（资源组、创建时间等）

## 技术背景

### 项目架构
- **后端**：FastAPI，使用模块化路由
- **前端**：Next.js 16 + React 19 + TypeScript
- **API 路由**：
  - `web/backend/api_resources.py` - 新模块化 API（已实现 ACK 详细信息）
  - `web/backend/api.py` - Legacy API（后注册，覆盖了新 API）

### 代码状态

#### ✅ 已完成的代码

1. **后端实现** (`web/backend/api_resources.py:436-567`)
   - `get_resource_detail()` 函数已实现 ACK 详细信息解析
   - 当 `resource_type == "ack"` 时，会解析 `raw_data` 并返回 `ack_details`
   - 包含完整的 Kubernetes 信息、网络配置、插件信息等

2. **前端实现** (`web/frontend/app/_pages/resource-detail.tsx:237-400`)
   - 已添加 4 个信息卡片组件
   - 已添加 `ack_details` 类型定义
   - 条件渲染：`{resource.type === "ack" && resource.ack_details && (...)}`

3. **数据模型** (`models/resource.py`)
   - `UnifiedResource` 已支持 `raw_data` 字段
   - ACK 资源创建时已保存完整原始数据到 `raw_data`

#### ❌ 问题所在

**核心问题**：FastAPI 路由冲突导致新 API 未被调用

1. **路由注册顺序** (`web/backend/main.py`)
   ```python
   # 第 88 行：先注册 api_resources
   api_modules = [..., ("api_resources", "资源管理"), ...]
   
   # 第 144 行：后注册 legacy api.py（覆盖了前面的路由）
   from web.backend.api import router as legacy_api_router
   app.include_router(legacy_api_router, tags=["Legacy"])
   ```

2. **路由路径冲突**
   - `api_resources.py`: `@router.get("/resources/{resource_id}")` (prefix="/api")
   - `api.py`: `@router.get("/resources/{resource_id}")` (prefix="/api")
   - FastAPI 后注册的路由会覆盖先注册的

3. **转发逻辑未生效** (`web/backend/api.py:1407-1417`)
   ```python
   if resource_type:
       try:
           from web.backend.api_resources import get_resource_detail
           result = get_resource_detail(resource_id, account, resource_type)
           if result.get('success') and result.get('data'):
               return result
       except Exception as e:
           logger.warning(f"转发到新 API 失败: {e}, 使用旧逻辑")
   ```
   - 直接调用 Python 函数时，转发成功 ✅
   - 通过 HTTP API 调用时，转发逻辑似乎未执行 ❌

## 测试结果

### ✅ 成功的测试

1. **直接调用新 API 函数**
   ```python
   from web.backend.api_resources import get_resource_detail
   result = get_resource_detail("c503e6d502a1a469aa87d68663129c116", "ydzn", "ack")
   # 结果：✅ 返回了 ack_details
   ```

2. **直接调用 Legacy API 函数（带转发）**
   ```python
   from web.backend.api import get_resource
   result = get_resource("c503e6d502a1a469aa87d68663129c116", "ydzn", "ack")
   # 结果：✅ 转发成功，返回了 ack_details
   ```

### ❌ 失败的测试

1. **HTTP API 调用**
   ```bash
   curl "http://localhost:8000/api/resources/c503e6d502a1a469aa87d68663129c116?type=ack&account=ydzn"
   # 结果：❌ 返回的数据中没有 ack_details 字段
   # 返回的字段：['id', 'name', 'type', 'status', 'region', 'spec', 'cost', 'tags', 'created_time', 'public_ips', 'private_ips', 'vpc_id']
   ```

## 问题分析

### 可能的原因

1. **FastAPI 路由匹配问题**
   - HTTP 请求可能没有进入 `api.py` 的 `get_resource` 函数
   - 或者进入了但没有执行转发逻辑

2. **参数传递问题**
   - `resource_type` 参数可能没有正确传递到函数
   - FastAPI 的 Query 参数解析可能有问题

3. **异常被静默捕获**
   - 转发逻辑中的异常可能被捕获但没有记录
   - 导致回退到旧逻辑

### 调试信息

- 后端日志中没有看到转发相关的日志（已添加但未输出）
- 说明可能没有进入转发逻辑，或者日志级别设置问题

## 解决方案建议

### 方案 1：修复路由优先级（推荐）

在 `web/backend/main.py` 中，调整路由注册顺序或移除冲突路由：

```python
# 方案 1A：移除 legacy API 的资源详情端点
from web.backend.api import router as legacy_api_router
# 移除冲突的路由
legacy_routes = [
    r for r in legacy_api_router.routes 
    if not (hasattr(r, 'path') and '/resources/{resource_id}' in r.path and hasattr(r, 'methods') and 'GET' in r.methods)
]
legacy_api_router.routes = legacy_routes
app.include_router(legacy_api_router, tags=["Legacy"])

# 方案 1B：调整路由注册顺序，让 api_resources 后注册（优先级更高）
# 但需要确保不影响其他 legacy 端点
```

### 方案 2：修复转发逻辑

确保 `api.py` 中的转发逻辑正确执行：

```python
@router.get("/resources/{resource_id}")
def get_resource(
    resource_id: str, 
    account: Optional[str] = None,
    resource_type: Optional[str] = Query(None, description="资源类型")
):
    """获取资源详情"""
    # 添加调试日志
    logger.info(f"Legacy API 被调用: resource_id={resource_id}, type={resource_type}, account={account}")
    
    # 如果提供了 resource_type，优先使用新 API
    if resource_type:
        try:
            from web.backend.api_resources import get_resource_detail
            logger.info(f"转发到新 API...")
            result = get_resource_detail(resource_id, account, resource_type)
            logger.info(f"新 API 返回: success={result.get('success')}, has_data={bool(result.get('data'))}")
            if result.get('success') and result.get('data'):
                logger.info(f"✅ 转发成功，返回新 API 结果")
                return result
            else:
                logger.warning(f"新 API 返回失败，使用旧逻辑")
        except Exception as e:
            logger.error(f"转发到新 API 失败: {e}", exc_info=True)
            # 继续执行旧逻辑
    
    # 旧逻辑...
```

### 方案 3：直接修复 Legacy API

在 `api.py` 的 `get_resource` 函数中，直接添加 ACK 详细信息的处理逻辑（不依赖转发）。

## 关键文件位置

1. **后端 API 实现**：
   - `web/backend/api_resources.py:436-567` - 新 API（已实现 ACK 详细信息）
   - `web/backend/api.py:1400-1529` - Legacy API（需要修复转发或直接实现）

2. **前端显示**：
   - `web/frontend/app/_pages/resource-detail.tsx:237-400` - ACK 详细信息 UI（已实现）

3. **路由注册**：
   - `web/backend/main.py:88-104` - 模块化 API 注册
   - `web/backend/main.py:142-149` - Legacy API 注册

4. **数据模型**：
   - `models/resource.py:32-76` - UnifiedResource 定义

## 测试命令

```bash
# 测试 HTTP API
curl "http://localhost:8000/api/resources/c503e6d502a1a469aa87d68663129c116?type=ack&account=ydzn" | jq '.data.ack_details'

# 期望输出：应该包含 ack_details 对象
# 实际输出：没有 ack_details 字段
```

## 当前状态

- ✅ 后端逻辑已实现（新 API）
- ✅ 前端 UI 已实现
- ✅ 数据模型已支持
- ❌ 路由冲突导致新 API 未被调用
- ❌ HTTP 请求返回的数据缺少 `ack_details`

## 下一步行动

1. 确认 HTTP 请求是否进入了 `api.py` 的 `get_resource` 函数
2. 确认 `resource_type` 参数是否正确传递
3. 修复路由冲突或转发逻辑
4. 验证 HTTP API 返回包含 `ack_details`
5. 刷新前端页面验证显示

