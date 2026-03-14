---
status: pending
priority: p1
issue_id: 007
tags: [agent-native, api, configuration, p1, code-review]
dependencies: []
created: 2026-03-15
---

# P1: 添加配置管理 API 端点

## Problem Statement

配置管理功能（关键词、评分规则）只有 UI 页面 (`/config/`)，但**没有对应的 API 端点**。这意味着：
- ❌ 代理无法查看或修改配置
- ❌ 无法通过 API 自动化配置管理
- ❌ 无法集成到 CI/CD 流程

**影响**: 代理原生性不足（60% 完成）

## Findings

### Agent-Native Review 发现：

**现有服务**:
```python
# src/web/services/config_service.py
class ConfigService:
    async def get_keywords(self) -> Dict:
        # 已实现
    
    async def update_keywords(self, keywords: Dict) -> None:
        # 已实现
    
    async def get_scoring_rules(self) -> Dict:
        # 已实现
```

**缺失的 API**:
- ❌ `GET /api/config/keywords` - 获取关键词配置
- ❌ `PUT /api/config/keywords` - 更新关键词配置
- ❌ `GET /api/config/scoring` - 获取评分规则
- ❌ `PUT /api/config/scoring` - 更新评分规则

**当前状态**:
- ✅ Service 层已实现
- ✅ UI 页面已实现
- ❌ API 端点缺失

### 对比：

| 功能 | UI | API | 代理可访问 |
|------|----|----|-----------|
| 查看配置 | ✅ | ❌ | ❌ |
| 修改配置 | ✅ | ❌ | ❌ |

## Proposed Solutions

### Solution 1: 完整 CRUD API (推荐)

**优点**:
- 完整功能覆盖
- 符合 RESTful 规范
- 支持版本控制和审计

**缺点**:
- 需要验证和权限控制

**工作量**: 2-3 小时

**风险**: 低

**实现步骤**:

1. **创建 `src/web/api/config.py`**:
```python
from fastapi import APIRouter, Depends
from src.web.services.config_service import ConfigService

router = APIRouter(prefix="/api/config", tags=["config-api"])

@router.get("/keywords")
async def get_keywords(
    service: ConfigService = Depends()
) -> Dict[str, Any]:
    """获取关键词配置"""
    return await service.get_keywords()

@router.put("/keywords")
async def update_keywords(
    keywords: Dict[str, Any],
    service: ConfigService = Depends()
) -> Dict[str, str]:
    """更新关键词配置"""
    await service.update_keywords(keywords)
    return {"status": "success"}

@router.get("/scoring")
async def get_scoring_rules(
    service: ConfigService = Depends()
) -> Dict[str, Any]:
    """获取评分规则"""
    return await service.get_scoring_rules()

@router.put("/scoring")
async def update_scoring_rules(
    rules: Dict[str, Any],
    service: ConfigService = Depends()
) -> Dict[str, str]:
    """更新评分规则"""
    await service.update_scoring_rules(rules)
    return {"status": "success"}
```

2. **注册路由**:
```python
# src/web/main.py
from src.web.api import config as config_api
app.include_router(config_api.router)
```

3. **添加 Pydantic Schema**:
```python
# src/web/schemas/config.py
from pydantic import BaseModel
from typing import Dict, List

class KeywordsConfig(BaseModel):
    english: List[str]
    chinese: List[str]
    core: List[str]
    equipment: List[str]

class ScoringConfig(BaseModel):
    weights: Dict[str, float]
    thresholds: Dict[str, int]
```

### Solution 2: 只读 API

**优点**:
- 实现简单
- 避免配置被误修改

**缺点**:
- 代理无法修改配置
- 功能不完整

**工作量**: 1 小时

**风险**: 低

## Recommended Action

**采用 Solution 1 (完整 CRUD API)**

原因：
1. 代理需要修改配置的能力
2. Service 层已实现，只需暴露 API
3. 工作量小（2-3 小时）

## Technical Details

**新增文件**:
- `src/web/api/config.py` (60-80 行)
- `src/web/schemas/config.py` (30-40 行)

**修改文件**:
- `src/web/main.py` - 注册路由

**API 端点**:
- `GET /api/config/keywords` - 获取关键词
- `PUT /api/config/keywords` - 更新关键词
- `GET /api/config/scoring` - 获取评分规则
- `PUT /api/config/scoring` - 更新评分规则

**认证要求**:
- ⚠️ PUT 端点需要认证（等 todo #001 完成后）
- GET 端点可以公开（或仅限内部网络）

## Acceptance Criteria

- [ ] 创建 `src/web/api/config.py`
- [ ] 4 个 API 端点全部实现
- [ ] API 文档正确生成（OpenAPI/Swagger）
- [ ] 测试：代理可以通过 API 获取配置
- [ ] 测试：代理可以通过 API 更新配置
- [ ] 配置更新持久化（保存到文件/数据库）
- [ ] 所有测试通过

## Work Log

### 2026-03-15
- Agent-Native Review 发现配置管理无 API
- Service 层已实现，只需暴露端点
- 优先级：P1（阻塞代理访问）
- 状态：待实施

## Resources

- ConfigService 实现: `src/web/services/config_service.py`
- Config UI 实现: `src/web/routes/config.py`
- RESTful API Design: https://restfulapi.net/
