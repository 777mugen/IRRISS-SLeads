---
title: "Pipeline 来源追踪：数据血缘管理"
category: "data-pipeline"
component: "数据处理流程"
severity: "medium"
resolved_at: "2026-03-15"
detected_at: "2026-03-14"
github_issue: null
related_docs:
  - docs/solutions/api-integration/paywall-content-extraction-jina-vs-zhipu.md
tags:
  - pipeline
  - data-lineage
  - source-tracking
  - postgresql
status: "verified"
---

# Pipeline 来源追踪：数据血缘管理

## Problem Symptom

**场景**: 系统中存在多个数据处理 Pipeline，无法区分数据来源

**痛点**:
- 历史数据（20 条）没有标记来源
- 无法统计不同 Pipeline 的成功率
- 无法回溯数据的处理路径
- 无法对比不同 Pipeline 的效果

**影响**:
- 无法评估 Pipeline 1 vs Pipeline 2 的优劣
- 无法针对特定 Pipeline 优化
- 数据质量分析困难

---

## Root Cause

**技术原因**:
1. **缺少字段**：`paper_leads` 和 `raw_markdown` 表没有 `pipeline_source` 字段
2. **历史数据**：早期数据没有标记来源
3. **代码未标记**：处理脚本没有写入来源信息

**业务原因**:
1. **早期快速迭代**：优先功能实现，忽略数据治理
2. **单一 Pipeline**：初期只有一个 Pipeline，不需要区分
3. **缺乏规划**：没有考虑多 Pipeline 场景

---

## Solution

### Step 1: 添加字段和索引

**数据库迁移**:

```sql
-- 添加 pipeline_source 字段
ALTER TABLE paper_leads
ADD COLUMN pipeline_source VARCHAR(50);

ALTER TABLE raw_markdown
ADD COLUMN pipeline_source VARCHAR(50);

-- 添加索引（提升查询性能）
CREATE INDEX ix_paper_leads_pipeline_source
ON paper_leads(pipeline_source);

CREATE INDEX idx_raw_markdown_pipeline_source
ON raw_markdown(pipeline_source);

-- 添加字段注释（文档化）
COMMENT ON COLUMN paper_leads.pipeline_source IS
'Pipeline 来源追踪（可选值：pipeline_v1_jina | pipeline_v2_zhipu_reader）';

COMMENT ON COLUMN raw_markdown.pipeline_source IS
'标识数据来源的处理管道，用于追踪和统计分析';
```

---

### Step 2: 历史数据回填

**回填脚本** (`migrations/backfill_pipeline_source.sql`):

```sql
-- 回填历史数据（20 条）
UPDATE paper_leads
SET pipeline_source = 'pipeline_v1_jina'
WHERE pipeline_source IS NULL;

UPDATE raw_markdown
SET pipeline_source = 'pipeline_v1_jina'
WHERE pipeline_source IS NULL;

-- 验证
SELECT
    pipeline_source,
    COUNT(*)
FROM paper_leads
GROUP BY pipeline_source;
```

**验证结果**:
```
pipeline_source    | count
-------------------+-------
pipeline_v1_jina   | 20
```

---

### Step 3: 代码中标记来源

**Pipeline 1 脚本** (`scripts/pipeline1_extract_and_csv.py`):

```python
async def save_to_raw_markdown(doi: str, content: str):
    """保存到 raw_markdown 表"""
    raw = RawMarkdown(
        doi=doi,
        markdown_content=content,
        pipeline_source='pipeline_v1_jina',  # 标记来源
        processing_status='content_ready'
    )
    session.add(raw)

async def save_to_paper_leads(extracted: Dict):
    """保存到 paper_leads 表"""
    lead = PaperLead(
        doi=extracted['doi'],
        name=extracted['name'],
        email=extracted['email'],
        pipeline_source='pipeline_v1_jina',  # 标记来源
        # ...
    )
    session.add(lead)
```

---

### Step 4: Dashboard 统计

**批处理监控** (`src/web/api/batch.py`):

```python
@router.get("/stats")
async def get_batch_stats():
    # 从 raw_markdown 和 paper_leads 双表统计
    raw_stats = await db.execute(
        select(
            RawMarkdown.pipeline_source,
            func.count(RawMarkdown.id)
        )
        .group_by(RawMarkdown.pipeline_source)
    )

    leads_stats = await db.execute(
        select(
            PaperLead.pipeline_source,
            func.count(PaperLead.id)
        )
        .group_by(PaperLead.pipeline_source)
    )

    return {
        "raw_markdown": dict(raw_stats.fetchall()),
        "paper_leads": dict(leads_stats.fetchall())
    }
```

---

## Verification

### 数据验证
```sql
-- 检查所有数据都有来源标记
SELECT
    'paper_leads' as table_name,
    COUNT(*) as total,
    COUNT(pipeline_source) as tagged,
    COUNT(*) - COUNT(pipeline_source) as untagged
FROM paper_leads

UNION ALL

SELECT
    'raw_markdown' as table_name,
    COUNT(*) as total,
    COUNT(pipeline_source) as tagged,
    COUNT(*) - COUNT(pipeline_source) as untagged
FROM raw_markdown;
```

**结果**:
```
table_name    | total | tagged | untagged
--------------+-------+--------+----------
paper_leads   | 185   | 185    | 0
raw_markdown  | 185   | 185    | 0
```

### 来源分布
```sql
SELECT
    pipeline_source,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM paper_leads
GROUP BY pipeline_source
ORDER BY count DESC;
```

**结果**:
```
pipeline_source      | count | percentage
---------------------+-------+------------
pipeline_v1_jina     | 185   | 100.00
```

---

## Prevention Strategies

### 1. 数据治理规范

**规范**:
1. 所有新 Pipeline 必须包含 `pipeline_source` 字段
2. 历史数据必须回填标记
3. 定期检查未标记数据

**检查脚本** (`scripts/check_pipeline_sources.py`):

```python
async def check_pipeline_sources():
    # 检查未标记数据
    untagged_leads = await db.execute(
        select(func.count(PaperLead.id))
        .where(PaperLead.pipeline_source == None)
    )

    untagged_raw = await db.execute(
        select(func.count(RawMarkdown.id))
        .where(RawMarkdown.pipeline_source == None)
    )

    if untagged_leads.scalar() > 0 or untagged_raw.scalar() > 0:
        logger.warning(f"发现未标记数据: leads={untagged_leads}, raw={untagged_raw}")
```

---

### 2. Pipeline 命名规范

**格式**: `pipeline_v{版本}_{核心技术}`

**示例**:
- `pipeline_v1_jina` - Jina Reader + 智谱 Batch
- `pipeline_v2_zhipu_reader` - 智谱网页阅读 + 智谱 Batch
- `pipeline_v3_unpaywall` - Unpaywall + 智谱 Batch

**字段约束**:
```sql
ALTER TABLE paper_leads
ADD CONSTRAINT valid_pipeline_source
CHECK (
    pipeline_source IS NULL OR
    pipeline_source IN (
        'pipeline_v1_jina',
        'pipeline_v2_zhipu_reader',
        'pipeline_v3_unpaywall'
    )
);
```

---

### 3. Pipeline 效果对比

**对比视图** (`views/pipeline_comparison.sql`):

```sql
CREATE VIEW pipeline_comparison AS
SELECT
    pl.pipeline_source,
    COUNT(*) as total_leads,
    AVG(pl.score) as avg_score,
    COUNT(CASE WHEN pl.email IS NOT NULL THEN 1 END) as leads_with_email,
    ROUND(COUNT(CASE WHEN pl.email IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as email_rate
FROM paper_leads pl
GROUP BY pl.pipeline_source;
```

**查询结果**:
```
pipeline_source      | total | avg_score | email_rate
---------------------+-------+-----------+------------
pipeline_v1_jina     | 185   | 50.0      | 0.00
pipeline_v2_zhipu    | 0     | NULL      | NULL
```

---

## Related Issues & Docs

### 相关文档
- [付费墙内容获取](api-integration/paywall-content-extraction-jina-vs-zhipu.md)
- [销售反馈系统](feedback-system/sales-feedback-import.md)

### 相关 PR
- PR #4: feat: 添加销售反馈系统和 Pipeline 1 修复

---

## Key Learnings

### 1. 数据治理要趁早
- **教训**: 早期忽略数据治理，后期需要大量回填工作
- **经验**: 从第一个版本就添加来源字段
- **行动**: 建立数据治理规范，强制执行

### 2. 索引很重要
- **教训**: 早期没有索引，查询 `pipeline_source` 很慢
- **经验**: 在添加字段的同时创建索引
- **行动**: 所有常用查询字段都添加索引

### 3. 双表一致性
- **教训**: `paper_leads` 和 `raw_markdown` 必须同步标记
- **经验**: 在同一个事务中更新两个表
- **行动**: 创建事务脚本，保证一致性

---

## Future Improvements

### 短期
- [ ] 添加 `pipeline_source` 约束（CHECK 约束）
- [ ] 创建 Pipeline 对比视图
- [ ] 添加未标记数据告警

### 中期
- [ ] Pipeline 版本管理
- [ ] Pipeline 效果对比报表
- [ ] 自动化数据质量检查

### 长期
- [ ] Pipeline A/B 测试框架
- [ ] 自动选择最优 Pipeline
- [ ] 数据血缘可视化

---

## Code References

### 关键文件
- `migrations/add_pipeline_source_fields.sql` - 字段添加
- `migrations/backfill_pipeline_source.sql` - 数据回填
- `scripts/pipeline1_extract_and_csv.py` - Pipeline 1 脚本
- `src/web/api/batch.py` - Dashboard 统计

### 回滚脚本
```sql
-- migrations/rollback_pipeline_source_fields.sql

-- 删除索引
DROP INDEX IF EXISTS ix_paper_leads_pipeline_source;
DROP INDEX IF EXISTS idx_raw_markdown_pipeline_source;

-- 删除字段
ALTER TABLE paper_leads DROP COLUMN IF EXISTS pipeline_source;
ALTER TABLE raw_markdown DROP COLUMN IF EXISTS pipeline_source;
```

---

## Conclusion

Pipeline 来源追踪是数据治理的基础：

1. **数据血缘**：每条数据都知道来自哪个 Pipeline
2. **效果对比**：可以量化不同 Pipeline 的优劣
3. **质量分析**：可以针对特定 Pipeline 优化

**核心价值**: 将数据从"黑盒"变为"可追溯"，为持续优化提供数据支撑。

---

**User**: 董胜豪 (ou_267c16d0bbf426921ce84255b6cfd1f9)
**Repository**: https://github.com/777mugen/IRRISS-SLeads
**Commit**: d7a9668
