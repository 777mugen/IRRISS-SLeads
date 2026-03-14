---
status: pending
priority: p1
issue_id: 008
tags: [agent-native, api, batch, retry, p1, code-review]
dependencies: []
created: 2026-03-15
---

# P1: 添加批处理重试 API 端点

## Problem Statement

批处理监控服务 (`BatchMonitor`) 有 `retry_failed_tasks()` 和 `reset_stale_tasks()` 方法，但**没有暴露对应的 API 端点**。

这意味着：
- ❌ 代理无法自动重试失败的任务
- ❌ 代理无法重置卡住的任务
- ❌ 需要人工干预才能恢复处理

**影响**: 自动化运维能力缺失

## Findings

### Agent-Native Review 发现：

**现有服务**:
```python
# src/monitoring/batch_monitor.py
class BatchMonitor:
    async def retry_failed_tasks(self, batch_id: str) -> int:
        """重试失败的任务"""
        # 已实现
        
    async def reset_stale_tasks(self, hours: int = 24) -> int:
        """重置卡住的任务"""
        # 已实现
```

**缺失的 API**:
- ❌ `POST /api/batch/retry` - 重试失败任务
- ❌ `POST /api/batch/reset-stale` - 重置卡住任务
- ❌ `GET /api/batch/retry-status` - 查询重试状态

**当前状态**:
- ✅ Service 层已实现
- ✅ 监控页面可以看到失败列表
- ❌ API 端点缺失

### 对比：

| 功能 | UI | API | 代理可访问 |
|------|-----|-----|----------|
| 查看失败任务 | ✅ | ✅ | ✅ |
| 重试失败任务 | ✅ | ❌ | ❌ |
| 重置卡住任务 | ❌ | ❌ | ❌ |

## Proposed Solutions

### Solution 1: 完整 API 实现 (推荐)

**优点**:
- 完整功能
- 代理可以自动化运维
- 符合 REST 最佳实践

**缺点**:
- 需要实现（但工作量小）

**工作量**: 2-3 小时

**风险**: 低

**实现步骤**:

1. **创建 API 端点**:
```python
# src/web/api/batch.py
from pydantic import BaseModel

class RetryRequest(BaseModel):
    batch_id: Optional[str] = None
    doi: Optional[str] = None

class ResetStaleRequest(BaseModel):
    hours: int = 24

@router.post("/retry")
async def retry_failed_tasks(
    request: RetryRequest,
    db: AsyncSession = Depends(get_db)
):
    """重试失败的任务"""
    monitor = BatchMonitor(db)
    
    if request.batch_id:
        count = await monitor.retry_failed_tasks(request.batch_id)
    elif request.doi:
        # 单个 DOI 重试
        count = await monitor.retry_single_doi(request.doi)
    else:
        # 重试所有失败任务
        count = await monitor.retry_all_failed()
    
    return {
        "status": "success",
        "retried_count": count
    }

@router.post("/reset-stale")
async def reset_stale_tasks(
    request: ResetStaleRequest,
    db: AsyncSession = Depends(get_db)
):
    """重置卡住的任务"""
    monitor = BatchMonitor(db)
    count = await monitor.reset_stale_tasks(request.hours)
    
    return {
        "status": "success",
        "reset_count": count
    }
```

2. **添加前端集成**:
```javascript
// src/web/templates/batch/monitor.html
async function retryPaper(doi) {
    const response = await fetch('/api/batch/retry', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({doi: doi})
    });
    const data = await response.json();
    alert(`已重试 ${data.retried_count} 个任务`);
    location.reload();
}

async function retryAllFailed() {
    if (confirm('确定要重试所有失败任务吗？')) {
        const response = await fetch('/api/batch/retry', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({})
        });
        const data = await response.json();
        alert(`已重试 ${data.retried_count} 个任务`);
        location.reload();
    }
}
```

### Solution 2: 批量重试 API

**优点**:
- 实现简单

**缺点**:
- 功能不完整
- 无法重置卡住任务

**工作量**: 1 小时

**风险**: 低

## Recommended Action

**采用 Solution 1 (完整 API)**

原因：
1. Service 层已实现，只需暴露端点
2. 工作量小
3. 完整功能

## Technical Details

**新增/修改文件**:
- `src/web/api/batch.py` - 添加 2 个端点（30-40 行）
- `src/web/templates/batch/monitor.html` - 添加前端集成（20-30 行）

**API 端点**:
- `POST /api/batch/retry` - 重试失败任务
  - Request body: `{"batch_id": "xxx", "doi": "10.1234/test"}` 或 `{}`
  - Response: `{"status": "success", "retried_count": 5}`
  
- `POST /api/batch/reset-stale` - 重置卡住任务
  - Request body: `{"hours": 24}`
  - Response: `{"status": "success", "reset_count": 3}`

**认证要求**:
- ⚠️ 需要认证（等 todo #001 完成后）

## Acceptance Criteria

- [ ] 创建 `POST /api/batch/retry` 端点
- [ ] 创建 `POST /api/batch/reset-stale` 端点
- [ ] API 文档正确生成
- [ ] 测试：单个 DOI 重试成功
- [ ] 测试：批量重试成功
- [ ] 测试：重置卡住任务成功
- [ ] 前端集成完成（重试按钮可用）
- [ ] 所有测试通过

## Work Log

### 2026-03-15
- Agent-Native Review 发现批处理重试无 API
- Service 层已实现，只需暴露端点
- 优先级：P1（影响自动化能力）
- 状态：待实施

## Resources

- BatchMonitor Service: `src/monitoring/batch_monitor.py`
- FastAPI Background Tasks: https://fastapi.tiangolo.com/tutorial/background-tasks/
