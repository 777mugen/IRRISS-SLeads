# 销售线索发现系统 V5

本目录是按照 Compound Engineering 工作流重组后的项目知识结构。

## Project Overview
自动化销售线索发现系统，面向免疫荧光领域。系统每日从论文与招标公告中发现潜在客户线索，提取结构化信息、评分、并输出 CSV 供销售团队使用。

核心流程：
数据源 → 抓取 → 字段提取 → 去重与标准化 → 评分 → CSV 输出 → 销售反馈 → 策略优化

## Core Architecture Docs

- docs/architecture/architecture_overview.md
- docs/architecture/data_sources.md
- docs/architecture/database_schema.md
- docs/architecture/scoring_rules.md
- docs/architecture/csv_output.md
- docs/architecture/error_handling.md
- docs/architecture/feedback_versioning.md
- docs/architecture/file_structure.md

这些文档定义系统行为，Agent 在实现功能前必须读取。

## Product Requirement

- docs/plans/requirements_v4.md

这是当前系统需求规格说明。

## Development Rules

1. 不满足基础字段的数据不允许入库。
2. URL 是唯一抓取去重标识。
3. 相同 `[姓名 + 单位 / 联系方式 / 地址]` 只保留最新线索。
4. 修改评分权重必须先通知 shane。
5. 禁止 DROP TABLE / TRUNCATE / 批量 DELETE。
6. 敏感信息只能存储在 `.env`。

## Compound Knowledge

- docs/solutions/ 用于记录解决方案与经验沉淀
- docs/brainstorms/ 用于探索阶段讨论

Agent 在实现功能完成后，应运行 compound 记录解决方案。
