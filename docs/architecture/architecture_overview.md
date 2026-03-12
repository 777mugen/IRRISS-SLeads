# System Architecture Overview

销售线索发现系统的核心架构：

Data Sources → Crawling → Extraction → Processing → Scoring → Export → Sales Feedback → Strategy Optimization

## Layers

1. Data Sources
论文数据库与政府采购网站。

2. Crawling Layer
使用 Jina Reader 与 Jina Search 获取网页内容。
必要时使用 Playwright 处理反爬站点。

3. Extraction Layer
使用 Claude API 从 Markdown 页面提取结构化字段（JSON）。

4. Processing Layer
数据去重、标准化、字段补齐。

5. Scoring Layer
根据评分规则生成数值评分与 ABCD 等级。

6. Export Layer
每日导出增量 CSV，每周导出全量 CSV。

7. Feedback Loop
销售反馈回流，用于优化关键词与评分策略。

## Key Design Principles

- 增量优先：避免重复抓取
- 配置驱动：规则在 YAML 中管理
- 软删除：数据不物理删除
- 可追溯：策略版本可回退
- Agent Friendly：结构清晰，便于 AI 自动化开发
