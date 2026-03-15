# Pipeline 来源追踪问题分析

## 🔴 当前问题

### 1. paper_leads 表

**现状**:
- ✅ 有 `source` 字段：论文来源（PubMed）
- ❌ **没有** pipeline 来源字段

**问题**: 无法区分数据来自哪个 pipeline

---

### 2. raw_markdown 表

**现状**:
- ✅ 有 `source_url`：DOI 链接
- ❌ **没有** pipeline 来源字段
- ❌ **没有** 内容获取方式字段

**问题**: 无法追踪内容获取方式

---

### 3. 新流程数据流向

```
新流程（智谱网页阅读 + 结构化输出）:
  ↓
raw_markdown 表 ✅ (会产生记录)
  ↓
paper_leads 表 ✅ (会产生记录)
```

**问题**: 
- ❌ 无法区分是 Jina 还是智谱网页阅读
- ❌ 可能重复（如果两个流程都运行）
- ❌ 难以追踪和调试

---

## 🛠️ 解决方案

### 方案 1: 添加 `extraction_method` 字段

#### paper_leads 表
```sql
ALTER TABLE paper_leads 
ADD COLUMN extraction_method VARCHAR(50);

-- 可能的值：
-- 'jina_batch' - Jina + 智谱 Batch
-- 'zhipu_reader_batch' - 智谱网页阅读 + 智谱 Batch
-- 'manual' - 手动录入
```

#### raw_markdown 表
```sql
ALTER TABLE raw_markdown 
ADD COLUMN fetch_method VARCHAR(50);

-- 可能的值：
-- 'jina_reader' - Jina Reader API
-- 'zhipu_reader' - 智谱网页阅读 API
-- 'pubmed_api' - PubMed API (摘要)
-- 'manual' - 手动上传
```

---

### 方案 2: 添加 `pipeline_source` 字段（推荐）

#### paper_leads 表
```sql
ALTER TABLE paper_leads 
ADD COLUMN pipeline_source VARCHAR(50);

COMMENT ON COLUMN paper_leads.pipeline_source IS 
'提取管道来源: pipeline_v1_jina, pipeline_v2_zhipu_reader';

-- 可能的值：
-- 'pipeline_v1_jina' - 旧流程（Jina + Batch）
-- 'pipeline_v2_zhipu_reader' - 新流程（智谱 Reader + Batch）
```

#### raw_markdown 表
```sql
ALTER TABLE raw_markdown 
ADD COLUMN pipeline_source VARCHAR(50);

COMMENT ON COLUMN raw_markdown.pipeline_source IS 
'内容获取管道: pipeline_v1_jina, pipeline_v2_zhipu_reader';

-- 可能的值：
-- 'pipeline_v1_jina' - 旧流程（Jina Reader）
-- 'pipeline_v2_zhipu_reader' - 新流程（智谱网页阅读）
```

---

## 📊 数据区分示例

### 更新后的 paper_leads 表

| id | doi | source | pipeline_source | ... |
|----|-----|--------|----------------|-----|
| 1 | 10.1234/a | PubMed | pipeline_v1_jina | ... |
| 2 | 10.1234/b | PubMed | pipeline_v2_zhipu_reader | ... |
| 3 | 10.1234/c | PubMed | pipeline_v1_jina | ... |

### 更新后的 raw_markdown 表

| id | doi | pipeline_source | processing_status | ... |
|----|-----|----------------|------------------|-----|
| 1 | 10.1234/a | pipeline_v1_jina | completed | ... |
| 2 | 10.1234/b | pipeline_v2_zhipu_reader | completed | ... |

---

## 🎯 Web Dashboard 增强

### 监控面板

```
┌─────────────────────────────────────────┐
│  Pipeline 分布统计                       │
├─────────────────────────────────────────┤
│  Pipeline V1 (Jina):      156 篇 (20%)  │
│  Pipeline V2 (智谱 Reader): 624 篇 (80%)│
│  成功率对比:                              │
│    V1: 20% ❌                            │
│    V2: 85% ✅                            │
└─────────────────────────────────────────┘
```

### 查询面板

```
筛选条件:
- Pipeline 来源: [全部] [V1-Jina] [V2-智谱]
- 处理状态: [全部] [成功] [失败]
- 日期范围: [2026-03-01] 至 [2026-03-15]
```

---

## 📝 实施步骤

### 步骤 1: 数据库迁移

```sql
-- 添加字段
ALTER TABLE paper_leads 
ADD COLUMN pipeline_source VARCHAR(50);

ALTER TABLE raw_markdown 
ADD COLUMN pipeline_source VARCHAR(50);

-- 添加索引（可选，用于查询优化）
CREATE INDEX ix_paper_leads_pipeline_source 
ON paper_leads(pipeline_source);

CREATE INDEX ix_raw_markdown_pipeline_source 
ON raw_markdown(pipeline_source);

-- 添加注释
COMMENT ON COLUMN paper_leads.pipeline_source IS 
'提取管道: pipeline_v1_jina, pipeline_v2_zhipu_reader';

COMMENT ON COLUMN raw_markdown.pipeline_source IS 
'内容获取管道: pipeline_v1_jina, pipeline_v2_zhipu_reader';
```

### 步骤 2: 更新 models.py

```python
class PaperLead(Base):
    # ... 现有字段 ...
    
    # 添加 pipeline 来源字段
    pipeline_source: Mapped[Optional[str]] = mapped_column(
        String(50), 
        nullable=True
    )  # 'pipeline_v1_jina' | 'pipeline_v2_zhipu_reader'
    
    __table_args__ = (
        # ... 现有索引 ...
        Index('ix_paper_leads_pipeline_source', 'pipeline_source'),
    )


class RawMarkdown(Base):
    # ... 现有字段 ...
    
    # 添加 pipeline 来源字段
    pipeline_source: Mapped[Optional[str]] = mapped_column(
        String(50), 
        nullable=True
    )  # 'pipeline_v1_jina' | 'pipeline_v2_zhipu_reader'
    
    __table_args__ = (
        # ... 现有索引 ...
        Index('ix_raw_markdown_pipeline_source', 'pipeline_source'),
    )
```

### 步骤 3: 更新 pipeline 代码

#### pipeline.py (旧流程)
```python
async def process_paper_with_doi(self, ...):
    lead = PaperLead(
        # ... 现有字段 ...
        pipeline_source='pipeline_v1_jina'  # ✅ 标记来源
    )
```

#### extract_with_zhipu_reader.py (新流程)
```python
async def extract_papers_with_zhipu_reader(...):
    # 保存到 raw_markdown
    raw = RawMarkdown(
        doi=doi,
        markdown_content=content,
        pipeline_source='pipeline_v2_zhipu_reader'  # ✅ 标记来源
    )
    
    # 保存到 paper_leads
    lead = PaperLead(
        # ... 提取的字段 ...
        pipeline_source='pipeline_v2_zhipu_reader'  # ✅ 标记来源
    )
```

### 步骤 4: 更新 Web Dashboard

```python
# src/web/api/query.py

async def search_leads(
    pipeline_source: Optional[str] = None,
    ...
):
    query = select(PaperLead)
    
    if pipeline_source:
        query = query.where(
            PaperLead.pipeline_source == pipeline_source
        )
    
    # ...
```

---

## ⚠️ 防止数据重复

### 方案 A: 唯一约束（推荐）

```sql
-- 在 paper_leads 表上添加唯一约束
-- 确保同一 DOI 只能有一条记录
ALTER TABLE paper_leads 
ADD CONSTRAINT uq_paper_leads_doi UNIQUE (doi);

-- 如果已经存在重复数据，需要先清理：
-- 1. 保留最新的记录
-- 2. 删除旧记录
DELETE FROM paper_leads 
WHERE id NOT IN (
    SELECT MAX(id) 
    FROM paper_leads 
    GROUP BY doi
);
```

### 方案 B: 逻辑检查

```python
async def process_paper(self, doi: str, ...):
    # 检查是否已存在
    existing = await self.check_doi_exists(doi)
    
    if existing:
        logger.info(f"DOI {doi} 已存在，跳过")
        return existing
    
    # 处理新记录
    lead = await self.extract_and_save(...)
    return lead
```

---

## 📈 统计查询示例

### 1. 统计各 pipeline 的处理量

```sql
SELECT 
    pipeline_source,
    COUNT(*) as total,
    COUNT(CASE WHEN grade = 'A' THEN 1 END) as grade_a,
    AVG(score) as avg_score
FROM paper_leads
GROUP BY pipeline_source;
```

### 2. 对比两个 pipeline 的成功率

```sql
SELECT 
    rm.pipeline_source,
    COUNT(rm.doi) as total_raw,
    COUNT(pl.doi) as total_leads,
    ROUND(COUNT(pl.doi)::numeric / COUNT(rm.doi) * 100, 2) as success_rate
FROM raw_markdown rm
LEFT JOIN paper_leads pl ON rm.doi = pl.doi
GROUP BY rm.pipeline_source;
```

### 3. 找出两个 pipeline 都处理过的 DOI

```sql
SELECT doi
FROM paper_leads
GROUP BY doi
HAVING COUNT(DISTINCT pipeline_source) > 1;
```

---

## ✅ 总结

### 当前状态
- ❌ 无法区分 pipeline 来源
- ❌ 可能重复数据
- ❌ 难以追踪和调试

### 修复后
- ✅ 清晰的 pipeline 来源标记
- ✅ 防止重复数据
- ✅ 支持统计分析
- ✅ Web Dashboard 可视化

### 优先级
- **P0**: 添加 `pipeline_source` 字段
- **P0**: 更新新流程脚本
- **P1**: 添加唯一约束
- **P2**: 更新 Web Dashboard

---

**建议立即实施步骤 1-3，确保数据可追溯！**