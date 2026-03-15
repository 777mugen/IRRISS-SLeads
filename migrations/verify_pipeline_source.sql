-- 验证 pipeline_source 字段
-- Date: 2026-03-15

-- 1. 检查 paper_leads 表
SELECT 
    'paper_leads' as table_name,
    COUNT(*) as total,
    COUNT(pipeline_source) as tagged,
    COUNT(*) - COUNT(pipeline_source) as untagged
FROM paper_leads;

-- 2. 检查 raw_markdown 表
SELECT 
    'raw_markdown' as table_name,
    COUNT(*) as total,
    COUNT(pipeline_source) as tagged,
    COUNT(*) - COUNT(pipeline_source) as untagged
FROM raw_markdown;

-- 3. 统计各 pipeline 的分布
SELECT 
    pipeline_source,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM paper_leads
GROUP BY pipeline_source
ORDER BY count DESC;

-- 4. 检查是否有重复的 DOI
SELECT 
    doi,
    COUNT(*) as duplicate_count,
    STRING_AGG(pipeline_source, ', ') as sources
FROM paper_leads
WHERE doi IS NOT NULL
GROUP BY doi
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC
LIMIT 10;

-- 5. 统计各 pipeline 的成功率
SELECT 
    rm.pipeline_source,
    COUNT(rm.doi) as total_raw,
    COUNT(pl.doi) as total_leads,
    ROUND(
        COUNT(pl.doi)::numeric / NULLIF(COUNT(rm.doi), 0) * 100, 
        2
    ) as success_rate
FROM raw_markdown rm
LEFT JOIN paper_leads pl ON rm.doi = pl.doi
GROUP BY rm.pipeline_source
ORDER BY total_raw DESC;
