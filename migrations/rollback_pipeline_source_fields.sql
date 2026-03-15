-- 回滚 pipeline_source 字段
-- Migration: rollback_pipeline_source_fields
-- Date: 2026-03-15

-- ============================================================================
-- 步骤 1: 删除索引
-- ============================================================================

-- 删除 paper_leads 表的索引
DROP INDEX IF EXISTS ix_paper_leads_pipeline_source;

-- 删除 raw_markdown 表的索引
DROP INDEX IF EXISTS idx_raw_markdown_pipeline_source;

-- ============================================================================
-- 步骤 2: 删除字段
-- ============================================================================

-- 删除 paper_leads 表的字段
ALTER TABLE paper_leads 
DROP COLUMN IF EXISTS pipeline_source;

-- 删除 raw_markdown 表的字段
ALTER TABLE raw_markdown 
DROP COLUMN IF EXISTS pipeline_source;

-- ============================================================================
-- 步骤 3: 验证
-- ============================================================================

-- 检查字段是否已删除
SELECT 
    table_name,
    column_name
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('paper_leads', 'raw_markdown')
  AND column_name = 'pipeline_source';

-- 应该返回 0 行（字段已删除）

-- ============================================================================
-- 说明
-- ============================================================================

-- ⚠️  警告：此操作将删除 pipeline_source 字段及所有数据
-- 
-- 影响范围：
-- 1. 无法追踪数据来源（pipeline_v1_jina / pipeline_v2_zhipu_reader）
-- 2. 无法按 pipeline 分组统计
-- 3. Web Dashboard 的 pipeline 筛选功能失效
-- 
-- 建议：
-- - 仅在确认不需要 pipeline 追踪功能时执行
-- - 执行前备份数据：pg_dump -t paper_leads -t raw_markdown
-- 
-- 回滚到添加字段前的状态：
-- - 执行 migrations/add_pipeline_source_fields.sql
