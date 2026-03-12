# 数据库 Schema

## 核心表

- raw_markdown（新增）
- paper_leads
- tender_leads
- feedback（新增）
- crawled_urls

---

## raw_markdown（新增）

存储论文的原始 Markdown 内容，支持重新提取。

**用途**:
- 存储 Jina Reader 返回的原始 Markdown
- 支持字段补齐时重新提取
- 避免重复调用 Jina API

### 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL PK | 自增主键 |
| doi | VARCHAR UNIQUE | DOI（外键） |
| pmid | VARCHAR | PMID |
| markdown_content | TEXT | Markdown 原始内容 |
| source_url | VARCHAR | 原始链接（https://doi.org/[DOI]） |
| fetched_at | TIMESTAMP | 获取时间 |
| created_at | TIMESTAMP | 创建时间 |

### 索引

```sql
CREATE INDEX idx_raw_markdown_doi ON raw_markdown(doi);
CREATE INDEX idx_raw_markdown_pmid ON raw_markdown(pmid);
```

---

## paper_leads

论文线索主表。

### 字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | SERIAL PK | ✅ | 自增主键 |
| doi | VARCHAR UNIQUE | ❌ | DOI 标识符 |
| pmid | VARCHAR UNIQUE | ❌ | PubMed ID |
| title | VARCHAR | ✅ | 文章标题 |
| published_at | DATE | ✅ | 发表时间 |
| article_url | VARCHAR | ✅ | 原文链接（https://doi.org/[DOI]） |
| source | VARCHAR(50) | ✅ | 来源（PubMed） |
| name | VARCHAR | ✅ | 通讯作者姓名 |
| institution | VARCHAR | ❌ | 通讯作者单位 |
| address | VARCHAR | ✅ | 通讯作者地址 |
| email | VARCHAR | ✅ | 通讯作者邮箱 |
| phone | VARCHAR | ✅ | 通讯作者电话 |
| all_authors | TEXT | ❌ | 全部作者信息（JSON 格式） |
| score | INTEGER | ❌ | 数值分数（0-100） |
| grade | VARCHAR(1) | ❌ | 等级（A/B/C/D） |
| feedback_status | VARCHAR(20) | ❌ | 反馈状态（默认"未处理"） |
| is_archived | BOOLEAN | ✅ | 是否归档（默认 false） |
| created_at | TIMESTAMP | ✅ | 创建时间 |
| updated_at | TIMESTAMP | ✅ | 更新时间 |

### 必须字段（任意缺失触发重新爬取）

- title（标题）
- published_at（发表时间）
- article_url（原文链接）
- source（来源）
- name（通讯作者）
- address（单位地址）
- phone（联系电话）
- email（电子邮箱）

### 索引

```sql
CREATE INDEX idx_paper_leads_doi ON paper_leads(doi);
CREATE INDEX idx_paper_leads_pmid ON paper_leads(pmid);
CREATE INDEX idx_paper_leads_grade ON paper_leads(grade);
CREATE INDEX idx_paper_leads_source ON paper_leads(source);
CREATE INDEX idx_paper_leads_created_at ON paper_leads(created_at);
```

---

## tender_leads

招标线索表（暂不重构，保持现有结构）。

### 核心字段

- id
- source_url
- announcement_id
- project_name
- published_at
- organization
- address
- email
- name
- phone
- org_only
- budget_info
- keywords_matched
- score
- grade
- feedback_status
- is_archived
- created_at
- updated_at

---

## feedback（新增）

销售反馈表，记录每条线索的实际使用情况。

### 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL PK | 自增主键 |
| paper_lead_id | INTEGER FK | 关联 paper_leads.id |
| accuracy | VARCHAR(10) | 线索准确性（好/中/差） |
| demand_match | VARCHAR(10) | 需求匹配度（好/中/差） |
| contact_validity | VARCHAR(10) | 联系方式有效性（好/中/差） |
| deal_speed | VARCHAR(10) | 成交速度（好/中/差） |
| deal_price | VARCHAR(10) | 成交价格（好/中/差） |
| notes | TEXT | 销售备注 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### 约束

```sql
FOREIGN KEY (paper_lead_id) REFERENCES paper_leads(id) ON DELETE CASCADE
```

---

## crawled_urls

记录已抓取 URL，用于增量控制。

### 字段

- url (PK)
- source_type
- crawled_at
- status

---

## Schema 约束

- ✅ 所有 schema 变更必须通过 Alembic
- ✅ 禁止 DROP TABLE
- ✅ 禁止 TRUNCATE（除非明确指令）
- ✅ 批量 DELETE 前必须确认

---

## 数据迁移注意事项

### 重构时的数据清理

```sql
-- 清空所有表（仅重构时执行）
TRUNCATE TABLE paper_leads CASCADE;
TRUNCATE TABLE tender_leads CASCADE;
TRUNCATE TABLE crawled_urls CASCADE;
TRUNCATE TABLE raw_markdown CASCADE;
TRUNCATE TABLE feedback CASCADE;
```

### DOI 作为唯一标识

- DOI 是通往全文链接的唯一官方凭证
- 大部分论文都有 DOI
- DOI 允许 NULL，但有值时必须唯一
- PMID 同样允许 NULL，但有值时必须唯一
