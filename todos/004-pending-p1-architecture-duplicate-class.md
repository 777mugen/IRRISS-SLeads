---
status: complete
priority: p1
issue_id: 004
tags: [architecture, naming, duplicate, p1, code-review]
dependencies: []
created: 2026-03-15
completed: 2026-03-15
---

# P1: 解决 ExportService 类名冲突

## Problem Statement

两个不同的文件定义了相同名称的 `ExportService` 类，导致：
- 命名空间污染
- 导入冲突
- 维护困难（开发者不知道修改哪个）
- 潜在的运行时错误

## Findings

### 冲突的类定义：

**文件 1: `src/web/services/export_service.py:12`**
```python
class ExportService:
    """导出服务"""
    async def get_paper_leads_for_export(...):
        # 导出论文线索
```

**文件 2: `src/web/services/feedback_service.py:15`**
```python
class ExportService:
    """CSV 导入导出服务"""
    async def export_paper_leads(...):
        # 导出论文线索
    
    async def import_feedback(...):
        # 导入反馈数据
```

### Architecture Review 发现：

这两个类：
- 有相同名称但不同职责
- `export_service.py` 专注于导出
- `feedback_service.py` 包含导出和导入
- 功能重叠，职责不清

## Proposed Solutions

### Solution 1: 重命名 FeedbackImportService (推荐)

**优点**:
- 语义清晰
- 职责分离
- 最小改动

**缺点**:
- 需要更新所有导入

**工作量**: 30 分钟

**风险**: 低

**实现步骤**:
1. 将 `feedback_service.py` 中的 `ExportService` 重命名为 `FeedbackImportService`
2. 更新所有引用（如果有）
3. 删除 `feedback_service.py` 中的导出方法（已在 `export_service.py` 中）

**示例代码**:
```python
# src/web/services/feedback_service.py
class FeedbackImportService:  # 重命名
    """反馈数据导入服务"""
    
    async def import_feedback_csv(...):
        # 导入反馈数据
    
    # 移除导出方法（已在 export_service.py）
```

### Solution 2: 合并两个服务

**优点**:
- 统一管理导入导出
- 减少文件数量

**缺点**:
- 违反单一职责原则
- 文件变大

**工作量**: 1-2 小时

**风险**: 中（可能引入 bug）

**实现步骤**:
1. 将 `feedback_service.py` 的导入方法合并到 `export_service.py`
2. 更新类名为 `ImportExportService`
3. 删除 `feedback_service.py`
4. 更新所有引用

### Solution 3: 完全分离职责

**优点**:
- 最清晰
- 符合单一职责原则

**缺点**:
- 需要创建更多文件

**工作量**: 2-3 小时

**风险**: 低

**实现步骤**:
1. 保留 `export_service.py` - 仅导出
2. 重命名 `feedback_service.py` → `feedback_import_service.py`
3. 创建 `paper_lead_export_service.py` - 专门的论文导出
4. 更新所有引用

## Recommended Action

**采用 Solution 1 (重命名)**

原因：
1. 改动最小
2. 立即解决冲突
3. 职责清晰

## Technical Details

**受影响文件**:
- `src/web/services/feedback_service.py` - 重命名类
- `src/web/api/import_csv.py` - 更新导入（如果有）
- 其他引用此类的文件

**修改**:
```python
# 之前:
from src.web.services.feedback_service import ExportService

# 之后:
from src.web.services.feedback_service import FeedbackImportService
```

## Acceptance Criteria

- [ ] `ExportService` 类名只在一个文件中定义
- [ ] `FeedbackImportService` 类名清晰反映职责
- [ ] 所有导入更新完成
- [ ] 所有测试通过
- [ ] 无运行时错误

## Work Log

### 2026-03-15
- Architecture Review 和 Quality Review 都发现类名冲突
- 两个审查代理确认这是关键问题
- 优先级：P1（立即解决）
- 状态：待修复

## Resources

- Python Naming Conventions: https://peps.python.org/pep-0008/#class-names
- Single Responsibility Principle: https://en.wikipedia.org/wiki/Single-responsibility_principle
