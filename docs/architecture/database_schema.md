# 数据库 Schema

核心表：

- crawled_urls
- paper_leads
- tender_leads
- strategy_versions

## crawled_urls
记录已抓取 URL，用于增量控制。

字段：
url (PK)
source_type
crawled_at
status

## paper_leads
论文线索主表。

核心字段：
id
source_url
title
published_at
institution
address
email
name
phone
keywords_matched
score
grade
feedback_status
strategy_version
is_archived
created_at
updated_at

## tender_leads
招标线索主表。

核心字段：
id
source_url
announcement_id
project_name
published_at
organization
address
email
name
org_only
budget_info
keywords_matched
score
grade
feedback_status
strategy_version
is_archived
created_at
updated_at

## strategy_versions
策略版本记录。

字段：
version
config_snapshot
change_reason
changed_by
is_active
created_at

## Schema Constraints

- 所有 schema 变更必须通过 Alembic
- 禁止 DROP TABLE
- 禁止 TRUNCATE
- 禁止批量 DELETE
