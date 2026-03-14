---
status: pending
priority: p1
issue_id: 009
tags: [agent-native, api, crud, p1, code-review]
dependencies: []
created: 2026-03-15
---

# P1: 添加更新/删除 API 端点

## Problem Statement

API 只有 Create（CSV 导入）和 Read（查询），但**没有 Update 或 Delete 操作**。

这意味着：
- ❌ 代理无法纠正错误数据
- ❌ 代理无法删除过时记录
- ❌ 数据无法通过 API 维护

**影响**: 数据管理能力不完整（违反 CRUD 原则）

## Findings

### Agent-Native Review 发现：

**现有 API**:
- ✅ Create: `POST /api/import/csv/confirm` - 批量导入反馈
- ✅ Read: `GET /api/query/doi` - 查询论文
- ✅ Read: `GET /api/analysis/stats` - 查询统计

**缺失的 API**:
- ❌ Update: `PUT /api/paper/{doi}` - 更新论文信息
- ❌ Delete: `DELETE /api/paper/{doi}` - 删除论文记录
- ❌ Update: `PUT /api/feedback/{id}` - 更新反馈
- ❌ Delete: `DELETE /api/feedback/{id}` - 删除反馈

### 对比：

| 操作 | PaperLead | Feedback |
|------|-----------|----------|
| Create | ✅ (CSV) | ✅ (CSV) |
| Read | ✅ | ✅ |
| **Update** | ❌ | ❌ |
| **Delete** | ❌ | ❌ |

## Proposed Solutions

### Solution 1: 完整 CRUD API (推荐)

**优点**:
- 完整的 REST API
- 数据可维护
- 符合最佳实践

**缺点**:
- 需要实现（但工作量适中）

**工作量**: 4-6 小时

**风险**: 低

**实现步骤**:

1. **PaperLead API**:
```python
# src/web/api/paper.py
from fastapi import HTTPException
from pydantic import BaseModel

class PaperUpdate(BaseModel):
    name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    institution_cn: Optional[str]
    score: Optional[int]
    grade: Optional[str]

@router.put("/{doi}")
async def update_paper(
    doi: str,
    update: PaperUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新论文信息"""
    result = await db.execute(
        select(PaperLead).where(PaperLead.doi == doi)
    )
    paper = result.scalar_one_or_none()
    
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")
    
    # 更新字段
    for field, value in update.dict(exclude_unset=True).items():
        setattr(paper, field, value)
    
    await db.commit()
    return {"status": "success", "doi": doi}

@router.delete("/{doi}")
async def delete_paper(
    doi: str,
    db: AsyncSession = Depends(get_db)
):
    """删除论文记录"""
    result = await db.execute(
        select(PaperLead).where(PaperLead.doi == doi)
    )
    paper = result.scalar_one_or_none()
    
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")
    
    await db.delete(paper)
    await db.commit()
    
    return {"status": "success", "deleted_doi": doi}
```

2. **Feedback API**:
```python
# src/web/api/feedback.py
from pydantic import BaseModel

class FeedbackUpdate(BaseModel):
    accuracy: Optional[str]
    demand_match: Optional[str]
    contact_validity: Optional[str]
    deal_speed: Optional[str]
    deal_price: Optional[str]
    notes: Optional[str]

@router.put("/{feedback_id}")
async def update_feedback(
    feedback_id: int,
    update: FeedbackUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新反馈"""
    result = await db.execute(
        select(Feedback).where(Feedback.id == feedback_id)
    )
    feedback = result.scalar_one_or_none()
    
    if not feedback:
        raise HTTPException(status_code=404, detail="反馈不存在")
    
    for field, value in update.dict(exclude_unset=True).items():
        setattr(feedback, field, value)
    
    await db.commit()
    return {"status": "success", "feedback_id": feedback_id}

@router.delete("/{feedback_id}")
async def delete_feedback(
    feedback_id: int,
    db: AsyncSession = Depends(get_db)
):
    """删除反馈"""
    result = await db.execute(
        select(Feedback).where(Feedback.id == feedback_id)
    )
    feedback = result.scalar_one_or_none()
    
    if not feedback:
        raise HTTPException(status_code=404, detail="反馈不存在")
    
    await db.delete(feedback)
    await db.commit()
    
    return {"status": "success", "deleted_id": feedback_id}
```

3. **注册路由**:
```python
# src/web/main.py
from src.web.api import paper as paper_api
from src.web.api import feedback as feedback_api

app.include_router(paper_api.router)
app.include_router(feedback_api.router)
```

### Solution 2: 批量操作 API

**优点**:
- 适合批量修正数据

**缺点**:
- 不是标准 REST
- 粒度较粗

**工作量**: 3-4 小时

**风险**: 中

## Recommended Action

**采用 Solution 1 (完整 CRUD API)**

原因：
1. 标准做法
2. 粒度适中
3. 易于使用

## Technical Details

**新增文件**:
- `src/web/api/paper.py` (80-100 行)
- `src/web/api/feedback.py` (70-90 行)

**API 端点**:
- `PUT /api/paper/{doi}` - 更新论文
- `DELETE /api/paper/{doi}` - 删除论文
- `PUT /api/feedback/{id}` - 更新反馈
- `DELETE /api/feedback/{id}` - 删除反馈

**认证要求**:
- ⚠️ 需要认证（等 todo #001 完成后）
- ⚠️ 可能需要管理员权限

**安全考虑**:
- 删除操作需要确认
- 更新操作需要验证
- 软删除 vs 硬删除（考虑软删除）

## Acceptance Criteria

- [ ] 创建 `src/web/api/paper.py`
- [ ] 创建 `src/web/api/feedback.py`
- [ ] 4 个 API 端点全部实现
- [ ] API 文档正确生成
- [ ] 测试：更新论文信息成功
- [ ] 测试：删除论文记录成功
- [ ] 测试：更新反馈成功
- [ ] 测试：删除反馈成功
- [ ] 404 错误正确处理
- [ ] 所有测试通过

## Work Log

### 2026-03-15
- Agent-Native Review 发现无 Update/Delete API
- 违反 CRUD 原则
- 优先级：P1（数据管理不完整）
- 状态：待实施

## Resources

- REST API Best Practices: https://stackoverflow.blog/2020/03/02/best-practices-for-rest-api-design/
- CRUD Operations: https://en.wikipedia.org/wiki/Create,_read,_update_and_delete
- FastAPI CRUD: https://fastapi.tiangolo.com/tutorial/sql-databases/
