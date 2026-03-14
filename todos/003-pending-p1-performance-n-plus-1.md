---
status: complete
priority: p1
issue_id: 003
tags: [performance, database, n+1, sql, p1, code-review]
dependencies: []
created: 2026-03-15
completed: 2026-03-15
---

# P1: 修复 N+1 查询问题（6 处）

## Problem Statement

代码中存在 **6 处 N+1 查询问题**，每个请求会导致数百次数据库往返，严重影响性能和可扩展性。

**性能影响**:
- 100 个 DOI 查询 → 200+ 次数据库调用（应该只需 2 次）
- 100 行 CSV 导入 → 200 次数据库调用（应该只需 2 次）
- 响应时间增加 5-10 倍

## Findings

### 1. `/api/query/doi` - DOI 批量查询 (query.py:23-61)

**当前代码**:
```python
for doi in request.dois:
    # 每次循环 2 个查询：
    raw = await db.execute(select(RawMarkdown).where(...))  # 查询 1
    lead = await db.execute(select(PaperLead).where(...))    # 查询 2
```

**问题**: 100 个 DOI = 200 次数据库查询

**优化后**:
```python
# 批量查询所有 DOI
raws = await db.execute(
    select(RawMarkdown).where(RawMarkdown.doi.in_(dois))
)
leads = await db.execute(
    select(PaperLead).where(PaperLead.doi.in_(dois))
)
# 100 个 DOI = 2 次数据库查询
```

**性能提升**: 95% 减少数据库调用

### 2. CSV 导入预览 (import_csv.py:44-51)

**当前代码**:
```python
for doi in df["DOI"]:
    result = await db.execute(
        select(PaperLead.id).where(PaperLead.doi == doi)
    )
```

**优化后**:
```python
dois = df["DOI"].tolist()
result = await db.execute(
    select(PaperLead.doi, PaperLead.id)
    .where(PaperLead.doi.in_(dois))
)
matched = {row.doi: row.id for row in result}
```

**性能提升**: 95% 减少

### 3. CSV 导入执行 (import_csv.py:77-103)

**当前代码**:
```python
for _, row in df.iterrows():
    paper_id = await db.execute(...)  # 查询
    feedback = Feedback(...)           # 插入
    db.add(feedback)
```

**优化后**:
```python
# 批量查询所有 DOI
paper_ids = await batch_fetch_paper_ids(df["DOI"])
# 批量插入所有反馈
feedbacks = [Feedback(...) for ...]
db.add_all(feedbacks)
```

**性能提升**: 从 O(2N) 到 O(2) 查询

### 4. 其他 N+1 位置

- `analysis.py` - Python 聚合而非 SQL
- `export_service.py` - 可优化但影响较小
- `batch.py` - 限制 20 条，影响较小

## Proposed Solutions

### Solution 1: 批量查询 + 字典映射 (推荐)

**优点**:
- 简单直接
- 性能提升显著（95%）
- 无需额外依赖

**缺点**:
- 需要重构查询逻辑

**工作量**: 6-8 小时（6 处）

**风险**: 低

**实现步骤**:
1. 修改 `query.py` - 批量查询 DOI
2. 修改 `import_csv.py` - 预览和导入都批量查询
3. 修改 `analysis.py` - SQL 聚合替代 Python 聚合
4. 测试所有修改

### Solution 2: 使用 SQLAlchemy 的 joinedload

**优点**:
- ORM 原生支持
- 自动优化

**缺点**:
- 仅适用于关联查询
- 当前场景不适用

**工作量**: 不适用

### Solution 3: 缓存层

**优点**:
- 减少重复查询
- 适用于频繁访问的数据

**缺点**:
- 引入复杂性
- 需要缓存失效策略
- 不解决根本问题

**工作量**: 1-2 天

**风险**: 中

## Recommended Action

**采用 Solution 1 (批量查询)**

原因：
1. 直接解决根本问题
2. 性能提升最大
3. 实现简单

## Technical Details

**受影响文件**:
- `src/web/api/query.py` (39 行需要重构)
- `src/web/api/import_csv.py` (60 行需要重构)
- `src/web/api/analysis.py` (50 行需要重构)

**总计**: 约 150 行需要修改

**性能提升预估**:
- DOI 查询（100 个）: 5s → 0.2s (25 倍加速)
- CSV 导入（100 行）: 3s → 0.15s (20 倍加速)
- 分析统计: 2s → 0.2s (10 倍加速)

## Acceptance Criteria

- [ ] `/api/query/doi` - 100 个 DOI 只需 2 次数据库查询
- [ ] CSV 导入预览 - N 行只需 1 次查询
- [ ] CSV 导入执行 - N 行只需 2 次查询
- [ ] 所有查询性能测试通过（<500ms）
- [ ] 无功能回归
- [ ] 代码审查通过

## Work Log

### 2026-03-15
- Performance Review 发现 6 处 N+1 查询问题
- 预估性能提升：10-25 倍
- 优先级：P1（严重影响性能）
- 状态：待修复

## Resources

- SQLAlchemy IN clause: https://docs.sqlalchemy.org/en/14/core/sqlelement.html#sqlalchemy.sql.expression.in_
- N+1 Problem: https://www.sqlshack.com/what-is-the-n1-query-problem/
- Batch Query Pattern: https://docs.sqlalchemy.org/en/14/orm/query.html#sqlalchemy.orm.Query.in_
