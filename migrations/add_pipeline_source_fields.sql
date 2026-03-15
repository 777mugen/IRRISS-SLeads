-- 添加 pipeline_source 字段
-- Migration: add_pipeline_source_fields
-- Date: 2026-03-15

-- ============================================================================
-- 步骤 1: 添加字段
-- ============================================================================

-- 为 paper_leads 表添加 pipeline_source 字段
ALTER TABLE paper_leads 
ADD COLUMN IF NOT EXISTS pipeline_source VARCHAR(50);

COMMENT ON COLUMN paper_leads.pipeline_source IS 
'提取管道来源: pipeline_v1_jina, pipeline_v2_zhipu_reader';

-- 为 raw_markdown 表添加 pipeline_source 字段
ALTER TABLE raw_markdown 
ADD COLUMN IF NOT EXISTS pipeline_source VARCHAR(50);

COMMENT ON COLUMN raw_markdown.pipeline_source IS 
'内容获取管道: pipeline_v1_jina, pipeline_v2_zhipu_reader';

-- ============================================================================
-- 步骤 2: 添加索引
-- ============================================================================

-- 为 paper_leads.pipeline_source 添加索引
CREATE INDEX IF NOT EXISTS ix_paper_leads_pipeline_source 
ON paper_leads(pipeline_source);

-- 为 raw_markdown.pipeline_source 添加索引
CREATE INDEX IF NOT EXISTS ix_raw_markdown_pipeline_source 
ON raw_markdown(pipeline_source);

-- ============================================================================
-- 步骤 3: 回填历史数据（带验证）
-- ============================================================================

-- 回填 paper_leads 表的历史数据
-- ✅ 只回填旧数据（2026-03-15 之前），避免误标记手动插入的数据
UPDATE paper_leads 
SET pipeline_source = 'pipeline_v1_jina'
WHERE pipeline_source IS NULL
  AND created_at < '2026-03-15 00:00:00';

-- 验证回填结果
DO $$
DECLARE
    untagged_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO untagged_count
    FROM paper_leads
    WHERE pipeline_source IS NULL
      AND created_at < '2026-03-15 00:00:00';
    
    IF untagged_count > 0 THEN
        RAISE NOTICE '⚠️  仍有 % 条旧数据未标记，请检查', untagged_count;
    ELSE
        RAISE NOTICE '✅ 所有旧数据已成功标记为 pipeline_v1_jina';
    END IF;
END $$;

-- 回填 raw_markdown 表的历史数据
-- ✅ 只回填旧数据（2026-03-15 之前）
UPDATE raw_markdown 
SET pipeline_source = 'pipeline_v1_jina'
WHERE pipeline_source IS NULL
  AND created_at < '2026-03-15 00:00:00';

-- 验证回填结果
DO $$
DECLARE
    untagged_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO untagged_count
    FROM raw_markdown
    WHERE pipeline_source IS NULL
      AND created_at < '2026-03-15 00:00:00';
    
    IF untagged_count > 0 THEN
        RAISE NOTICE '⚠️  仍有 % 条旧数据未标记，请检查', untagged_count;
    ELSE
        RAISE NOTICE '✅ 所有旧数据已成功标记为 pipeline_v1_jina';
    END IF;
END $$;

-- ============================================================================
-- 步骤 4: 验证
-- ============================================================================

-- 检查是否有未标记的记录
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

-- ============================================================================
-- 步骤 5: 统计（可选）
-- ============================================================================

-- 统计各 pipeline 的处理量
SELECT 
    pipeline_source,
    COUNT(*) as total_count,
    MIN(created_at) as first_created,
    MAX(created_at) as last_created
FROM paper_leads
GROUP BY pipeline_source
ORDER BY total_count DESC;
