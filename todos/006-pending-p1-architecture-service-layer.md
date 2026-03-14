---
status: pending
priority: p1
issue_id: 006
tags: [architecture, refactoring, solid, p1, code-review]
dependencies: [004]
created: 2026-03-15
---

# P1: 重构 - 将业务逻辑从 API 端点移到服务层

## Problem Statement

API 端点包含大量业务逻辑（数据库查询、数据转换、CSV 生成），违反单一职责原则。这导致：
- 代码难以测试（必须模拟 HTTP 请求）
- 业务逻辑不可重用（无法在 CLI 或后台任务中使用）
- 紧耦合（HTTP 层与业务逻辑混杂）

## Findings

### Architecture Review 发现：

**违反原则**:
- ❌ 单一职责原则 (SRP) - API 做了太多事
- ❌ 开闭原则 (OCP) - 添加功能需修改 API 端点
- ❌ 依赖倒置原则 (DIP) - 高层模块依赖低层模块

**受影响文件**:

1. **`src/web/api/export.py` (79-129 行)**
   - CSV 生成逻辑应该在服务层
   - 数据库查询应该在 Repository 层

2. **`src/web/api/analysis.py` (22-78 行)**
   - 统计分析逻辑应该在服务层
   - Python 聚合应该改为 SQL

3. **`src/web/api/query.py` (23-61 行)**
   - DOI 查询逻辑应该在服务层
   - N+1 查询问题

4. **`src/web/api/import_csv.py` (44-103 行)**
   - CSV 导入逻辑与 `feedback_service.py` 重复

### Current Architecture:

```
API Endpoint
├── HTTP Request/Response Handling
├── Business Logic (❌ 应该在 Service)
├── Database Queries (❌ 应该在 Repository)
└── Data Transformation (❌ 应该在 Service)
```

### Recommended Architecture:

```
API Endpoint (薄控制器)
├── HTTP Request/Response Handling ✅
└── Delegates to Service → Service Delegates to Repository → Database
```

## Proposed Solutions

### Solution 1: 完整重构 (推荐)

**优点**:
- 彻底解决架构问题
- 遵循 SOLID 原则
- 易于测试和维护

**缺点**:
- 工作量大
- 短期风险较高

**工作量**: 3-5 天

**风险**: 中

**实现步骤**:

1. **创建 Repository 层**:
   ```
   src/web/repositories/
   ├── paper_lead_repository.py
   ├── feedback_repository.py
   └── raw_markdown_repository.py
   ```

2. **重构 Service 层**:
   - `export_service.py` - 添加 CSV 生成逻辑
   - `analysis_service.py` - 新建，包含统计逻辑
   - `query_service.py` - 新建，包含查询逻辑

3. **简化 API 端点**:
   ```python
   # 之前 (79 行代码):
   @router.get("/csv/full")
   async def export_full_csv(db: AsyncSession = Depends(get_db)):
       papers = await db.execute(select(PaperLead)...)
       output = io.StringIO()
       writer = csv.writer(output)
       # ... 50 行 CSV 生成逻辑
   
   # 之后 (10 行代码):
   @router.get("/csv/full")
   async def export_full_csv(service: ExportService = Depends()):
       return await service.export_full_csv()
   ```

### Solution 2: 渐进式重构

**优点**:
- 风险更低
- 可以逐步迁移
- 不影响现有功能

**缺点**:
- 持续时间长
- 临时性架构混乱

**工作量**: 1-2 周（分散）

**风险**: 低

**实现步骤**:
1. 先重构最复杂的 API（export、analysis）
2. 新功能强制使用 Service 层
3. 逐步迁移旧代码

## Recommended Action

**采用 Solution 1 (完整重构)**

原因：
1. 项目刚起步，重构成本低
2. 长期收益大（可维护性、可测试性）
3. 避免"技术债务"累积

## Technical Details

**新增文件**:
- `src/web/repositories/paper_lead_repository.py`
- `src/web/repositories/feedback_repository.py`
- `src/web/repositories/raw_markdown_repository.py`
- `src/web/services/analysis_service.py`
- `src/web/services/query_service.py`

**重构文件**:
- `src/web/api/export.py` - 简化到 10-20 行
- `src/web/api/analysis.py` - 简化到 10-20 行
- `src/web/api/query.py` - 简化到 10-20 行
- `src/web/api/import_csv.py` - 简化到 20-30 行

**代码行数变化**:
- 删除：约 300 行（从 API 层）
- 新增：约 500 行（Service 和 Repository 层）
- 净增：200 行（但架构更清晰）

## Acceptance Criteria

- [ ] 所有业务逻辑移到 Service 层
- [ ] 所有数据库查询移到 Repository 层
- [ ] API 端点少于 30 行代码
- [ ] Service 层可以独立测试（无需 HTTP 模拟）
- [ ] Repository 层可以独立测试（无需完整数据库）
- [ ] 所有现有功能正常工作
- [ ] 所有测试通过

## Work Log

### 2026-03-15
- Architecture Review 发现业务逻辑在 API 端点中
- 违反 SOLID 原则
- 优先级：P1（架构问题）
- 状态：待重构

## Resources

- SOLID Principles: https://en.wikipedia.org/wiki/SOLID
- Repository Pattern: https://martinfowler.com/eaaCatalog/repository.html
- FastAPI Best Practices: https://github.com/zhanymkanov/fastapi-best-practices
