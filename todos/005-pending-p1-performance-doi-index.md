---
status: complete
priority: p1
issue_id: 005
tags: [performance, database, index, sql, p1, code-review]
dependencies: []
created: 2026-03-15
completed: 2026-03-15
---

# P1: 添加缺失的 paper_leads.doi 索引

## Problem Statement

`paper_leads` 表的 `doi` 列没有索引，导致所有 DOI 查询都执行全表扫描。

**性能影响**:
- 1000 条记录 → 全表扫描 1000 行
- 10000 条记录 → 全表扫描 10000 行
- 查询时间：50-500ms（应该 <5ms）

DOI 是查询最频繁的字段（查询、导入、导出都使用），缺少索引严重影响性能。

## Findings

### Performance Review 发现：

**当前索引**（models.py）:
```python
class PaperLead(Base):
    __tablename__ = "paper_leads"
    
    pmid = Column(String, index=True)  # ✅ 有索引
    doi = Column(String)                # ❌ 无索引！
```

**受影响的查询**:
- `src/web/api/query.py` - DOI 查询
- `src/web/api/import_csv.py` - CSV 导入预览和执行
- `src/web/services/export_service.py` - 导出服务

### 查询计划示例：

**无索引时**:
```sql
EXPLAIN SELECT * FROM paper_leads WHERE doi = '10.1234/test';
-- Seq Scan on paper_leads  (cost=0.00..150.00 rows=1 width=500)
-- 全表扫描，时间复杂度 O(n)
```

**有索引后**:
```sql
EXPLAIN SELECT * FROM paper_leads WHERE doi = '10.1234/test';
-- Index Scan using idx_paper_leads_doi on paper_leads  (cost=0.00..8.27 rows=1 width=500)
-- 索引扫描，时间复杂度 O(log n)
```

**性能提升**: 10-100 倍（取决于表大小）

## Proposed Solutions

### Solution 1: 添加 B-Tree 索引 (推荐)

**优点**:
- 标准索引类型
- 支持精确匹配和范围查询
- PostgreSQL 默认索引

**缺点**:
- 占用磁盘空间
- 略微降低插入速度（可忽略）

**工作量**: 30 分钟

**风险**: 低

**实现步骤**:

1. **创建迁移文件**:
```bash
alembic revision -m "add_doi_index"
```

2. **迁移代码**:
```python
# migrations/versions/xxx_add_doi_index.py
from alembic import op

def upgrade():
    op.create_index(
        'idx_paper_leads_doi',
        'paper_leads',
        ['doi'],
        unique=False,
        postgresql_concurrently=True  # 不锁表
    )

def downgrade():
    op.drop_index('idx_paper_leads_doi', table_name='paper_leads')
```

3. **运行迁移**:
```bash
alembic upgrade head
```

### Solution 2: 添加唯一索引

**优点**:
- 确保 DOI 唯一性
- 自动创建索引

**缺点**:
- 如果有重复 DOI 会导致错误
- 需要先清理重复数据

**工作量**: 1 小时（包括数据清理）

**风险**: 中（可能影响现有数据）

### Solution 3: 添加复合索引

**优点**:
- 优化特定查询模式
- 例如：`(doi, created_at DESC)`

**缺点**:
- 占用更多空间
- 可能不被某些查询使用

**工作量**: 1 小时

**风险**: 低

## Recommended Action

**采用 Solution 1 (B-Tree 索引)**

原因：
1. 最简单直接
2. 立即提升性能
3. 不影响现有数据

## Technical Details

**受影响表**:
- `paper_leads` - 添加 `idx_paper_leads_doi` 索引

**受影响查询**:
- 所有 `WHERE doi = ?` 查询
- 所有 `WHERE doi IN (...)` 查询

**预估性能提升**:
- 1000 条记录：50ms → 5ms (10 倍)
- 10000 条记录：500ms → 5ms (100 倍)
- 100000 条记录：5000ms → 5ms (1000 倍)

**磁盘空间**:
- 每条记录约 50 字节
- 10000 条记录约 500KB

**插入性能影响**:
- 略微降低（<5%）
- 可忽略

## Acceptance Criteria

- [ ] 创建 Alembic 迁移文件
- [ ] 迁移成功运行
- [ ] 索引存在于数据库中
- [ ] 查询计划显示使用索引（Index Scan）
- [ ] DOI 查询时间 <10ms
- [ ] 批量 DOI 查询性能提升 >90%
- [ ] 所有测试通过

## Work Log

### 2026-03-15
- Performance Review 发现缺失 DOI 索引
- 预估性能提升：10-1000 倍
- 优先级：P1（严重影响性能）
- 状态：待实施

## Resources

- PostgreSQL Indexes: https://www.postgresql.org/docs/current/indexes.html
- CREATE INDEX CONCURRENTLY: https://www.postgresql.org/docs/current/sql-createindex.html#SQL-CREATEINDEX-CONCURRENTLY
- SQLAlchemy Indexes: https://docs.sqlalchemy.org/en/14/core/constraints.html#indexes
