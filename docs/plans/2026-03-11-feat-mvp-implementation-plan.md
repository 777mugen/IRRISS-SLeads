---
title: MVP Implementation - Sales Lead Discovery System
type: feat
status: active
date: 2026-03-11
---

# MVP Implementation - Sales Lead Discovery System

## Overview

从零构建销售线索发现系统的 MVP 版本，实现：
- 每日自动从 PubMed 和政府采购网站抓取线索
- LLM 结构化字段提取
- 多维度评分
- CSV 导出

## Technical Approach

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Scheduler (APScheduler)                  │
│                      每日 06:00 触发                          │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┴───────────────────────────────┐
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   Crawlers   │───▶│  Extractors  │───▶│  Processors  │   │
│  │  Jina/Play   │    │   Claude     │    │  去重/标准化  │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│                                                │              │
│                                                ▼              │
│                                         ┌──────────────┐    │
│                                         │   Scoring    │    │
│                                         │   Engine     │    │
│                                         └──────────────┘    │
│                                                │              │
│                                                ▼              │
│                                         ┌──────────────┐    │
│                                         │  Exporters   │    │
│                                         │    CSV       │    │
│                                         └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                      ┌──────────────┐
                      │  PostgreSQL  │
                      │   Database   │
                      └──────────────┘
```

### Tech Stack

| 组件 | 技术 | 版本 |
|------|------|------|
| 语言 | Python | 3.14+ |
| 数据库 | PostgreSQL | 16+ |
| ORM | SQLAlchemy | 2.0+ |
| 迁移 | Alembic | 最新 |
| HTTP | httpx | 最新 |
| LLM | anthropic | 最新 |
| 调度 | APScheduler | 3.x |
| 数据处理 | pandas | 最新 |

## Implementation Phases

### Phase 1: Environment & Scaffolding

**目标**: 搭建项目骨架和开发环境

**任务**:

1. **安装 PostgreSQL**
   - 使用 Homebrew 安装
   - 创建数据库 `sleads_dev`
   - 配置用户权限

2. **项目脚手架**
   ```
   leads-discovery/
   ├── config/
   │   ├── keywords.yaml
   │   ├── sources.yaml
   │   ├── scoring_paper.yaml
   │   ├── scoring_tender.yaml
   │   └── scheduler.yaml
   ├── src/
   │   ├── __init__.py
   │   ├── crawlers/
   │   ├── extractors/
   │   ├── processors/
   │   ├── scoring/
   │   ├── exporters/
   │   ├── feedback/
   │   ├── versioning/
   │   ├── db/
   │   └── scheduler/
   ├── tests/
   ├── output/
   │   ├── paper_leads/
   │   └── tender_leads/
   ├── logs/
   ├── .env.example
   ├── requirements.txt
   └── pyproject.toml
   ```

3. **依赖配置**
   - requirements.txt
   - .env.example (模板)
   - .gitignore 更新

**验收标准**:
- [ ] PostgreSQL 运行正常
- [ ] 数据库 `sleads_dev` 创建成功
- [ ] 项目结构完整
- [ ] `pip install -r requirements.txt` 无错误
- [ ] `python -c "from src import db"` 正常

**估计时间**: 1-2 小时

---

### Phase 2: Database Layer

**目标**: 数据库模型和迁移系统

**任务**:

1. **SQLAlchemy 模型** (`src/db/models.py`)
   - `CrawledURL` - 已抓取 URL 记录
   - `PaperLead` - 论文线索
   - `TenderLead` - 招标线索
   - `StrategyVersion` - 策略版本

2. **Alembic 配置**
   - 初始化 Alembic
   - 创建初始迁移
   - 运行迁移脚本

3. **数据库工具** (`src/db/utils.py`)
   - 连接管理
   - Session 上下文
   - 批量插入辅助

**Schema 设计**:

```sql
-- crawled_urls: URL 去重表
CREATE TABLE crawled_urls (
    url TEXT PRIMARY KEY,
    source_type VARCHAR(20) NOT NULL,  -- 'paper' | 'tender'
    crawled_at TIMESTAMP NOT NULL,
    status VARCHAR(20) NOT NULL        -- 'success' | 'failed' | 'skipped'
);

-- paper_leads: 论文线索表
CREATE TABLE paper_leads (
    id SERIAL PRIMARY KEY,
    source_url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    published_at DATE,
    institution TEXT,
    address TEXT,
    email TEXT,
    name TEXT,
    phone TEXT,
    keywords_matched TEXT[],
    score INTEGER,
    grade CHAR(1),                     -- 'A' | 'B' | 'C' | 'D'
    feedback_status VARCHAR(20),       -- '未处理' | '已联系' | ...
    strategy_version VARCHAR(10),
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- tender_leads: 招标线索表
CREATE TABLE tender_leads (
    id SERIAL PRIMARY KEY,
    source_url TEXT UNIQUE NOT NULL,
    announcement_id TEXT,
    project_name TEXT NOT NULL,
    published_at DATE,
    organization TEXT,
    address TEXT,
    email TEXT,
    name TEXT,
    phone TEXT,
    org_only BOOLEAN DEFAULT FALSE,
    budget_info TEXT,
    keywords_matched TEXT[],
    score INTEGER,
    grade CHAR(1),
    feedback_status VARCHAR(20),
    strategy_version VARCHAR(10),
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- strategy_versions: 策略版本表
CREATE TABLE strategy_versions (
    version VARCHAR(10) PRIMARY KEY,
    config_snapshot JSONB NOT NULL,
    change_reason TEXT,
    changed_by VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**验收标准**:
- [ ] 所有表创建成功
- [ ] Alembic 迁移正常
- [ ] SQLAlchemy 模型 CRUD 测试通过
- [ ] 索引和约束正确

**估计时间**: 2-3 小时

---

### Phase 3: Configuration System

**目标**: 配置文件和加载机制

**任务**:

1. **关键词配置** (`config/keywords.yaml`)
   - 英文核心关键词
   - 中文核心关键词
   - 关联设备关键词

2. **数据源配置** (`config/sources.yaml`)
   - 论文数据源 URL
   - 招标数据源 URL
   - 优先级排序

3. **评分配置**
   - `config/scoring_paper.yaml` - 论文评分规则
   - `config/scoring_tender.yaml` - 招标评分规则

4. **调度配置** (`config/scheduler.yaml`)
   - 运行时间
   - 重试策略

5. **配置加载器** (`src/config/loader.py`)
   - YAML 解析
   - 环境变量覆盖
   - 验证和默认值

**验收标准**:
- [ ] 所有配置文件创建
- [ ] 配置加载器工作正常
- [ ] 环境变量覆盖生效

**估计时间**: 1 小时

---

### Phase 4: Jina API Integration

**目标**: Jina Reader 和 Search API 集成

**任务**:

1. **Jina Client** (`src/crawlers/jina_client.py`)
   ```python
   class JinaClient:
       async def search(self, query: str) -> list[str]
       async def read(self, url: str) -> str
   ```

2. **速率限制和重试**
   - 指数退避重试
   - 请求限流
   - 错误处理

3. **Playwright 兜底** (`src/crawlers/playwright_fallback.py`)
   - 用于 Jina 无法访问的页面
   - 验证码检测和通知

**验收标准**:
- [ ] Jina Search 返回 URL 列表
- [ ] Jina Reader 返回 Markdown 内容
- [ ] 重试机制正常
- [ ] 错误日志记录

**估计时间**: 2-3 小时

**依赖**: Jina API Key

---

### Phase 5: LLM Extraction

**目标**: Claude API 结构化提取

**任务**:

1. **提取器基类** (`src/extractors/base.py`)

2. **论文提取器** (`src/extractors/paper_extractor.py`)
   - Prompt 模板设计
   - 字段映射
   - 必填字段验证

3. **招标提取器** (`src/extractors/tender_extractor.py`)
   - Prompt 模板设计
   - 字段映射
   - org_only 标记

4. **Prompt 模板**
   - 论文提取 Prompt
   - 招标提取 Prompt
   - JSON 输出格式约束

**验收标准**:
- [ ] 论文页面 → JSON 字段提取成功
- [ ] 招标页面 → JSON 字段提取成功
- [ ] 必填字段缺失时不入库
- [ ] 提取结果符合 Schema

**估计时间**: 3-4 小时

**依赖**: Claude API Key

---

### Phase 6: PubMed Crawler (End-to-End)

**目标**: 完整的论文爬取流程

**任务**:

1. **PubMed 爬虫** (`src/crawlers/pubmed_crawler.py`)
   - 关键词搜索
   - URL 发现
   - 去重过滤
   - 页面读取

2. **完整流程集成**
   ```
   搜索 → 过滤已爬 → 读取 → 提取 → 入库
   ```

3. **增量控制**
   - 查询 crawled_urls 表
   - 只处理新 URL

**验收标准**:
- [ ] 搜索返回相关论文 URL
- [ ] 已爬 URL 不重复处理
- [ ] 新论文入库成功
- [ ] 日志记录完整

**估计时间**: 3-4 小时

---

### Phase 7: Scoring Engine

**目标**: 两套评分系统

**任务**:

1. **评分引擎基类** (`src/scoring/base.py`)
   - 评分维度抽象
   - 权重计算
   - 等级转换

2. **论文评分** (`src/scoring/paper_scorer.py`)
   - 信息完备度 (20%)
   - 匹配度 (25%)
   - 时效性 (20%)
   - 决策链条 (15%)
   - 机构类型 (10%)
   - 历史互动 (10%)

3. **招标评分** (`src/scoring/tender_scorer.py`)
   - 预算状态 (20%)
   - 匹配度 (20%)
   - 时效性 (20%)
   - 信息完备度 (15%)
   - 决策链条 (10%)
   - 机构类型 (10%)
   - 历史互动 (5%)

4. **机构识别** (`src/scoring/institution_matcher.py`)
   - 985/211/双一流列表
   - 三甲医院识别
   - 科研院所识别

**验收标准**:
- [ ] 论文评分 0-100 分正确
- [ ] 招标评分 0-100 分正确
- [ ] 等级 A/B/C/D 转换正确
- [ ] 机构类型识别准确

**估计时间**: 3-4 小时

---

### Phase 8: CSV Export

**目标**: 增量和全量导出

**任务**:

1. **CSV 导出器** (`src/exporters/csv_exporter.py`)
   - 论文线索导出
   - 招标线索导出

2. **增量导出**
   - 每日运行
   - 仅新增/变更记录

3. **全量导出**
   - 每周日运行
   - diff 标注 (新增/已更新/无变化)

4. **文件命名**
   - `paper_leads_incremental_YYYY-MM-DD.csv`
   - `paper_leads_full_YYYY-MM-DD.csv`
   - `tender_leads_incremental_YYYY-MM-DD.csv`
   - `tender_leads_full_YYYY-MM-DD.csv`

**验收标准**:
- [ ] 增量 CSV 格式正确
- [ ] 全量 CSV 包含 diff 标注
- [ ] 文件保存到 output/ 目录
- [ ] 字段与需求文档一致

**估计时间**: 2-3 小时

---

### Phase 9: Scheduler

**目标**: 定时任务调度

**任务**:

1. **APScheduler 配置** (`src/scheduler/scheduler.py`)
   - 每日 06:00 触发
   - 周日额外触发全量导出

2. **主任务流程** (`src/scheduler/tasks.py`)
   ```
   06:00 启动
     ├── 论文爬取 + 提取 + 入库
     ├── 招标爬取 + 提取 + 入库
     ├── 评分
     ├── 增量导出
     └── (周日) 全量导出
   10:00 完成
   ```

3. **日志和通知**
   - 任务开始/结束日志
   - 错误记录
   - (后续) 飞书通知

**验收标准**:
- [x] 定时任务正常触发
- [x] 完整流程无错误
- [x] 日志记录完整
- [x] 10:00 前完成

**估计时间**: 2-3 小时

**状态**: completed

---

## System-Wide Impact

### Error Propagation

| 层级 | 错误类型 | 处理方式 |
|------|----------|----------|
| 网络层 | 超时/连接失败 | 重试 1 次，记录日志 |
| API 层 | Jina/Claude 错误 | 重试，跳过当前 URL |
| 数据层 | 必填字段缺失 | 不入库，记录警告 |
| 调度层 | 任务失败 | 记录错误，次日重试 |

### State Lifecycle Risks

- **部分失败**: 单个 URL 失败不影响其他
- **去重保护**: URL 唯一约束防止重复入库
- **软删除**: 使用 is_archived 标记，不物理删除

## Acceptance Criteria

### Functional Requirements

- [ ] PostgreSQL 数据库运行正常
- [ ] 论文爬虫端到端工作
- [ ] 招标爬虫端到端工作
- [ ] 评分引擎产出 A/B/C/D 等级
- [ ] CSV 导出格式正确
- [ ] 定时任务每日 06:00 触发

### Non-Functional Requirements

- [ ] 日志保留 30 天
- [ ] API Key 不进入代码仓库
- [ ] 数据库禁止 DROP/TRUNCATE
- [ ] 评分权重变更需通知 shane

## Dependencies & Prerequisites

### 必需

| 依赖 | 状态 | 提供者 |
|------|------|--------|
| PostgreSQL 16+ | 待安装 | 系统 |
| Jina API Key | 待提供 | shane |
| Claude API Key | 待提供 | shane |

### 可选 (后续迭代)

- 飞书机器人 Webhook
- CNKI 数据源

## Risk Analysis & Mitigation

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 验证码拦截 | 高 | 中 | 立即通知，不自动处理 |
| API 费用超预期 | 中 | 中 | 监控使用量，设置阈值 |
| 数据源变更 | 中 | 高 | 模块化设计，易于适配 |
| 磁盘空间不足 | 低 | 高 | 日志自动清理 |

## Sources & References

### Internal References

- 需求文档: `需求说明文档.md`
- 架构设计: `docs/architecture/`
- 评分规则: `docs/architecture/scoring_rules.md`
- 数据源配置: `docs/architecture/data_sources.md`
