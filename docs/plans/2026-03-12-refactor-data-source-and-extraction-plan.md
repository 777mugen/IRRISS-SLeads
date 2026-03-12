---
title: SLeads 系统架构重构 - 数据源与提取层改造
type: refactor
status: active
date: 2026-03-12
origin: docs/plans/2026-03-12-refactoring-plan.md
---

# SLeads 系统架构重构 - 数据源与提取层改造

## Overview

重构 SLeads 销售线索发现系统的数据获取流程，从 Jina Search API 切换到官方 PubMed Entrez API + NCBI ID Converter API，同时改进数据存储策略、提取逻辑和增量爬取机制。

核心变更：
- **数据源层**: Jina Search → PubMed Entrez API + NCBI ID Converter API
- **存储层**: 新增 raw_markdown 表，DOI 作为唯一标识
- **提取层**: 两阶段 GLM-5 调用（定位 + 提取）
- **增量逻辑**: 基于字段完整性检查的智能重爬取

## Problem Statement / Motivation

### 当前问题

1. **数据源不可靠**
   - Jina Search API 结果有限（最多返回 10-20 条）
   - 无法精确控制搜索范围（时间、关键词）
   - 缺少官方 API 的合规性保障

2. **缺少原始数据存储**
   - Markdown 内容未被保存
   - 字段补齐需要重新获取全文
   - 无法验证提取结果的准确性

3. **提取效率低**
   - 单次 GLM-5 调用处理全文
   - 超长文本导致上下文溢出
   - 提取成功率低（33% in testing）

4. **增量逻辑不完善**
   - 缺少字段完整性检查
   - 已有数据无法补齐缺失字段
   - 重复爬取浪费资源

### 业务影响

- 销售线索数量受限（每天仅能获取少量新线索）
- 数据质量不稳定（字段缺失率高）
- 资源浪费（重复获取相同内容）

## Proposed Solution

### 核心架构变更

```
[旧流程]
关键词 → Jina Search → URL列表 → Jina Reader → Markdown → GLM-5 提取 → 入库

[新流程]
关键词 → PubMed Entrez API → PMID列表 → NCBI ID Converter → DOI列表 → 
Jina Reader → Markdown → 存储 raw_markdown → 
两阶段GLM-5提取 → 结构化JSON → 评分 → 入库 → CSV导出
```

### 关键设计决策

#### 1. DOI 作为唯一标识
- **原因**: DOI 是通往全文链接的唯一官方凭证
- **实现**: 
  - DOI 作为 paper_leads 表的 UNIQUE 约束
  - 允许 NULL（少数论文没有 DOI）
  - PMID 同样作为 UNIQUE 约束（允许 NULL）

#### 2. raw_markdown 表
- **原因**: 
  - 存储原始内容，  - 支持字段补齐重新提取
  - 验证提取准确性
- **实现**:
```sql
CREATE TABLE raw_markdown (
    id SERIAL PRIMARY KEY,
    doi VARCHAR UNIQUE NOT NULL,
    pmid VARCHAR,
    markdown_content TEXT NOT NULL,
    source_url VARCHAR NOT NULL,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3. 两阶段提取
- **阶段1**: 定位（Search）
  - 搜索关键词: Correspondence, Affiliation, Email
  - 返回位置信息（行号范围）
- **阶段2**: 提取（Extract）
  - 只处理指定区域内容
  - 避免全文上下文溢出
  - 提高提取成功率

#### 4. 字段完整性检查
- **必须字段**（任一缺失触发重新爬取）:
  - title (标题)
  - published_at (发表时间)
  - article_url (原文链接)
  - source (来源)
  - name (通讯作者)
  - address (单位地址)
  - phone (联系电话)
  - email (电子邮箱)

#### 5. feedback 表
- **5个反馈维度**（好/中/差）:
  - accuracy (线索准确性)
  - demand_match (需求匹配度)
  - contact_validity (联系方式有效性)
  - deal_speed (成交速度)
  - deal_price (成交价格)

## Technical Approach

### Phase 1: 数据库重构 (P0)

#### 任务清单

- [ ] 创建数据库迁移脚本
  - 清空现有数据（paper_leads, tender_leads, crawled_urls）
  - 新建 raw_markdown 表
  - 修改 paper_leads 表字段
  - 新建 feedback 表
  - 添加索引

#### SQL 迁移

```sql
-- 1. 清空现有数据
TRUNCATE TABLE paper_leads CASCADE;
TRUNCATE TABLE tender_leads CASCADE;
TRUNCATE TABLE crawled_urls CASCADE;

-- 2. 创建 raw_markdown 表
CREATE TABLE raw_markdown (
    id SERIAL PRIMARY KEY,
    doi VARCHAR UNIQUE NOT NULL,
    pmid VARCHAR,
    markdown_content TEXT NOT NULL,
    source_url VARCHAR NOT NULL,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. 修改 paper_leads 表
ALTER TABLE paper_leads 
    DROP COLUMN IF EXISTS keywords_matched,
    ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'PubMed',
    ADD COLUMN IF NOT EXISTS article_url VARCHAR;

ALTER TABLE paper_leads 
    ADD CONSTRAINT unique_doi UNIQUE (doi);

-- 4. 创建 feedback 表
CREATE TABLE feedback (
    id SERIAL PRIMARY KEY,
    paper_lead_id INTEGER REFERENCES paper_leads(id) ON DELETE CASCADE,
    accuracy VARCHAR(10),
    demand_match VARCHAR(10),
    contact_validity VARCHAR(10),
    deal_speed VARCHAR(10),
    deal_price VARCHAR(10),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. 创建索引
CREATE INDEX idx_raw_markdown_doi ON raw_markdown(doi);
CREATE INDEX idx_paper_leads_source ON paper_leads(source);
CREATE INDEX idx_feedback_paper_lead_id ON feedback(paper_lead_id);
```

#### 文件清单

- `alembic/versions/xxx_refactor_data_source.py` (新建迁移)
- `src/db/models.py` (更新模型)

---

### Phase 2: 数据源层重构 (P0)

#### 2.1 PubMed Entrez API 客户端

**文件**: `src/crawlers/pubmed_entrez.py`

```python
"""
PubMed Entrez API 客户端
官方文档: https://www.ncbi.nlm.nih.gov/books/NBK25500/
"""

import httpx
from typing import List
from datetime import date

class PubMedEntrezClient:
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    def __init__(self, email: str = "Shane@irriss.com", tool: str = "IRRISS-SLeads"):
        self.email = email
        self.tool = tool
        self.http = httpx.AsyncClient(timeout=30.0)
    
    async def search(
        self,
        query: str,
        max_results: int = 100,
        date_range: tuple[int, int] = None
    ) -> List[str]:
        """
        搜索论文，返回 PMID 列表
        
        API: esearch.fcgi
        限制: 3 requests/second
        """
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "email": self.email,
            "tool": self.tool
        }
        
        if date_range:
            start_year, end_year = date_range
            params["datetype"] = "pdat"
            params["mindate"] = f"{start_year}/01/01"
            params["maxdate"] = f"{end_year}/12/31"
        
        response = await self.http.get(
            f"{self.BASE_URL}/esearch.fcgi",
            params=params
        )
        
        data = response.json()
        return data.get("esearchresult", {}).get("idlist", [])
    
    async def fetch_details(self, pmids: List[str]) -> List[dict]:
        """
        获取论文详情
        
        API: efetch.fcgi
        返回: [{pmid, doi, title, abstract, ...}, ...]
        """
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "email": self.email,
            "tool": self.tool
        }
        
        response = await self.http.get(
            f"{self.BASE_URL}/efetch.fcgi",
            params=params
        )
        
        # 解析 XML，提取 DOI 等字段
        # TODO: 实现 XML 解析逻辑
        pass
```

**关键设计点**:
- 遵守 API 使用条款（email + tool name）
- 速率限制（3 requests/second）
- 时间范围筛选支持

#### 2.2 NCBI ID Converter API 客户端

**文件**: `src/crawlers/ncbi_id_converter.py`

```python
"""
NCBI ID Converter API 客户端
官方文档: https://www.ncbi.nlm.nih.gov/pmc/tools/id-converter-api/
"""

import httpx
from typing import Dict

class NCBIIDConverter:
    BASE_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=30.0)
    
    async def convert_pmids_to_dois(
        self,
        pmids: List[str]
    ) -> Dict[str, str]:
        """
        批量转换 PMID → DOI
        
        返回: {pmid: doi, ...}
        """
        params = {
            "ids": ",".join(pmids),
            "format": "json"
        }
        
        response = await self.http.get(self.BASE_URL, params=params)
        data = response.json()
        
        result = {}
        for record in data.get("records", []):
            pmid = record.get("pmid")
            doi = record.get("doi")
            if pmid and doi:
                result[pmid] = doi
        
        return result
```

#### 任务清单

- [ ] 实现 PubMedEntrezClient
  - esearch.fcgi 集成
  - efetch.fcgi 集成
  - XML 解析逻辑
  - 速率限制器

- [ ] 实现 NCBIIDConverter
  - 批量转换接口
  - 错误处理（无 DOI 的情况）

- [ ] 集成测试
  - 搜索功能测试
  - DOI 转换测试
  - 速率限制测试

---

### Phase 3: 提取层重构 (P0)

#### 3.1 两阶段提取器

**文件**: `src/extractors/two_stage_extractor.py`

```python
"""
两阶段提取器：先定位，再提取
解决超长文本上下文溢出问题
"""

class TwoStageExtractor:
    async def extract(self, markdown: str) -> dict:
        # Stage 1: 定位关键信息位置
        locations = await self._locate_keywords(markdown)
        
        # Stage 2: 提取指定区域内容
        result = await self._extract_fields(markdown, locations)
        
        return result
    
    async def _locate_keywords(self, markdown: str) -> dict:
        """
        阶段1: 定位
        
        Prompt 示例:
        在以下 Markdown 文本中，找到以下关键词出现的位置：
        - Correspondence / Corresponding Author
        - Affiliation
        - Email / E-mail
        - Phone / Telephone
        
        返回 JSON 格式：
        {
          "correspondence_start": <行号>,
          "correspondence_end": <行号>,
          "email_start": <行号>
        }
        """
        lines = markdown.split('\n')
        prompt = f"""
在以下 Markdown 文本中，找到以下关键词出现的位置：
- Correspondence / Corresponding Author
- Affiliation
- Email / E-mail
- Phone / Telephone

返回 JSON 格式：
{{
  "correspondence_start": <行号>,
  "correspondence_end": <行号>,
  "email_start": <行号>
}}

文本内容（前5000字符）：
{markdown[:5000]}
"""
        return await self.llm.call(prompt)
    
    async def _extract_fields(self, markdown: str, locations: dict) -> dict:
        """
        阶段2: 提取
        
        只处理指定区域，避免全文溢出
        """
        lines = markdown.split('\n')
        
        # 提取通讯作者区域
        start = locations.get('correspondence_start', 0)
        end = locations.get('correspondence_end', len(lines))
        correspondence_section = '\n'.join(lines[start:end])
        
        prompt = f"""
从以下文本片段中提取通讯作者信息：

通讯作者区域：
{correspondence_section}

返回 JSON 格式：
{{
  "name": "通讯作者姓名",
  "email": "邮箱",
  "phone": "电话",
  "institution": "单位",
  "address": "地址"
}}
"""
        return await self.llm.call(prompt)
```

#### 3.2 更新 PaperExtractor

**文件**: `src/extractors/paper_extractor.py`

**变更**:
- 移除 `keywords_matched` 字段
- 新增 `source` 字段（固定 "PubMed"）
- 新增 `article_url` 字段（https://doi.org/[DOI]）
- `all_authors` 保持 JSON 格式（CSV 导出时展开）

#### 任务清单

- [ ] 实现 TwoStageExtractor
  - 定位阶段 Prompt
  - 提取阶段 Prompt
  - 区域提取逻辑

- [ ] 更新 PaperExtractor
  - 移除 keywords_matched
  - 新增 source/article_url
  - 更新必填字段验证

- [ ] 集成测试
  - 两阶段提取测试
  - 超长文本处理测试

---

### Phase 4: Pipeline 重构 (P0)

#### 4.1 新的执行流程

**文件**: `src/pipeline.py`

```python
class LeadPipeline:
    async def process_paper(self, pmid: str, doi: str = None):
        """
        处理单篇论文
        
        流程：
        1. 检查 DOI 是否已存在
        2. 如果存在且字段完整 → 跳过
        3. 如果存在但字段缺失 → 重新提取
        4. 如果不存在 → 完整流程
        """
        # Step 1: 检查是否存在
        existing = await self.check_existing(doi or pmid)
        
        if existing and self.is_complete(existing):
            self.logger.info(f"跳过 {pmid}: 字段完整")
            return None
        
        # Step 2: 获取 DOI（如果没有）
        if not doi:
            doi = await self.convert_pmid_to_doi(pmid)
        
        # Step 3: 检查 raw_markdown 是否存在
        markdown = await self.get_raw_markdown(doi)
        
        if not markdown:
            # Step 4: 获取 Markdown
            article_url = f"https://doi.org/{doi}"
            markdown = await self.jina_reader.read(article_url)
            
            # Step 5: 存储 Markdown
            await self.save_raw_markdown(doi, pmid, markdown, article_url)
        
        # Step 6: 两阶段提取
        extracted = await self.two_stage_extract(markdown)
        
        # Step 7: 评分
        score, grade = await self.scorer.score(extracted)
        
        # Step 8: 入库
        lead = {
            'pmid': pmid,
            'doi': doi,
            'title': extracted['title'],
            'published_at': extracted['published_at'],
            'article_url': f"https://doi.org/{doi}",
            'source': 'PubMed',
            'name': extracted['corresponding_author']['name'],
            'email': extracted['corresponding_author']['email'],
            'phone': extracted['corresponding_author']['phone'],
            'institution': extracted['corresponding_author']['institution'],
            'address': extracted['corresponding_author']['address'],
            'all_authors': json.dumps(extracted['all_authors']),
            'score': score,
            'grade': grade
        }
        
        if existing:
            # 更新已有记录
            await self.update_lead(lead)
            # 发送飞书通知
            await self.feishu.send_update_notification(lead)
        else:
            # 新增记录
            await self.save_lead(lead)
        
        return lead
    
    def is_complete(self, lead: PaperLead) -> bool:
        """检查字段是否完整"""
        required = [
            lead.title,
            lead.published_at,
            lead.article_url,
            lead.source,
            lead.name,
            lead.address,
            lead.phone,
            lead.email
        ]
        return all(field is not None and field != '' for field in required)
```

#### 4.2 增量爬取逻辑

**关键判断**:
```python
if DOI 不存在:
    # 新线索
    完整处理流程
    
elif DOI 存在 and not is_complete(lead):
    # 字段缺失，重新提取
    if raw_markdown 存在:
        从 raw_markdown 重新提取
    else:
        重新获取 Markdown
    更新数据库
    发送飞书通知
    
else:
    # DOI 存在且字段完整
    跳过
```

#### 任务清单

- [ ] 重构 LeadPipeline
  - DOI 检查逻辑
  - 字段完整性检查
  - raw_markdown 复用逻辑
  - 增量更新逻辑

- [ ] 实现飞书更新通知
  - diff 报告生成
  - 直接更新（根据用户选择）

- [ ] 集成测试
  - 增量爬取测试
  - 字段补齐测试

---

### Phase 5: CSV 导出重构 (P0)

#### 5.1 字段调整

**文件**: `src/exporters/csv_exporter.py`

**新字段列表**:
```
DOI, 标题, 发表时间, 原文链接, 来源, 
通讯作者, 单位地址, 联系电话, 电子邮箱, 
其他作者信息, 线索等级
```

**移除字段**:
- `命中关键词` (keywords_matched)
- `分数` (只保留等级)

#### 5.2 其他作者信息展开

**数据库存储** (JSON):
```json
[
  {
    "name": "张三",
    "institution": "清华大学",
    "email": "abc@tsinghua.edu.cn",
    "phone": "+86-138-0000-0000"
  }
]
```

**CSV 导出** (一人一行):
```
张三, 清华大学, abc@tsinghua.edu.cn, +86-138-0000-0000
李四, 北京大学, def@pku.edu.cn, 
王五, 中科院, ghi@cas.cn, 
```

#### 任务清单

- [ ] 更新 CSVExporter
  - 移除 keywords_matched
  - 新增 source/article_url
  - 只导出 grade，不导出 score
  - all_authors JSON → 一人一行展开

- [ ] 集成测试
  - CSV 字段验证
  - 其他作者展开格式

---

### Phase 6: 销售反馈功能 (P0)

#### 6.1 feedback 表

**用途**: 记录销售对每条线索的反馈

**表结构**:
```sql
CREATE TABLE feedback (
    id SERIAL PRIMARY KEY,
    paper_lead_id INTEGER REFERENCES paper_leads(id) ON DELETE CASCADE,
    accuracy VARCHAR(10),           -- 线索准确性（好/中/差）
    demand_match VARCHAR(10),       -- 需求匹配度（好/中/差）
    contact_validity VARCHAR(10),   -- 联系方式有效性（好/中/差）
    deal_speed VARCHAR(10),         -- 成交速度（好/中/差）
    deal_price VARCHAR(10),         -- 成交价格（好/中/差）
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 6.2 使用流程

1. 销售在飞书多维表格中填入反馈（好/中/差）
2. 定期导出反馈数据
3. 系统分析反馈数据，生成优化建议
4. shane 审核后确认执行

#### 任务清单

- [ ] 创建 feedback 模型
  - 添加到 src/db/models.py
  - 外键关联到 paper_leads

- [ ] 实现反馈收集逻辑（P2 后续实现）

---

## System-Wide Impact

### Interaction Graph

**数据流**:
```
关键词 → PubMed Entrez → PMID列表 → NCBI ID Converter → DOI列表 → 
Jina Reader → Markdown → raw_markdown 存储 → 
两阶段GLM-5提取 → 结构化JSON → 评分 → paper_leads → CSV导出 → 飞书通知
```

**增量更新流**:
```
检查 DOI → 检查字段完整性 → 
  完整: 跳过
  缺失: 从 raw_markdown 重新提取 → 更新 → 飞书通知
```

### Error & Failure Propagation

1. **PubMed API 失败**
   - 速率限制 → 等待重试
   - 网络错误 → 记录日志，跳过本次搜索

2. **DOI 转换失败**
   - 记录无 DOI 的 PMID
   - 允许 DOI 为 NULL

3. **Jina Reader 失败**
   - 切换 Playwright
   - 记录失败状态

4. **GLM-5 提取失败**
   - JSON 解析失败 → 记录原始响应
   - 字段缺失 → 标记为"提取失败"
   - 不影响其他数据处理

5. **字段缺失**
   - 触发重新爬取逻辑
   - 从 raw_markdown 重新提取

### State Lifecycle Risks

1. **raw_markdown 孤立记录**
   - DOI 在 raw_markdown 但不在 paper_leads
   - 解决: 定期清理孤立记录

2. **部分提取失败**
   - 某些字段提取成功，某些失败
   - 解决: 逐字段验证，失败字段标记为 NULL

3. **重复 DOI**
   - UNIQUE 约束避免重复
   - 错误捕获：IntegrityError → 跳过

### API Surface Parity

**相关接口**:
- `src/crawlers/pubmed.py` → 删除（旧版）
- `src/crawlers/collectors.py` → 更新（使用新 API）
- `src/pipeline.py` → 重构（增量逻辑）
- `src/exporters/csv_exporter.py` → 更新（字段调整）

### Integration Test Scenarios

1. **完整流程测试**
   - 输入: 关键词
   - 验证: PMID → DOI → Markdown → 提取 → 评分 → CSV

2. **增量爬取测试**
   - 输入: 已存在的 DOI
   - 验证: 字段完整 → 跳过
   - 验证: 字段缺失 → 重新提取

3. **两阶段提取测试**
   - 输入: 超长文本（>10000 字符）
   - 验证: 定位成功 + 提取成功

4. **错误恢复测试**
   - 输入: 无 DOI 的 PMID
   - 验证: 正确处理 NULL DOI

5. **CSV 导出测试**
   - 输入: 包含多个作者的论文
   - 验证: 其他作者正确展开（一人一行）

---

## Acceptance Criteria

### Functional Requirements

- [ ] PubMed Entrez API 集成
  - 搜索功能正常
  - 速率限制生效
  - 时间范围筛选正常

- [ ] NCBI ID Converter API 集成
  - 批量转换 PMID → DOI
  - 正确处理无 DOI 情况

- [ ] raw_markdown 表
  - 正确存储 Markdown
  - DOI 唯一性约束生效
  - 外键关联正确

- [ ] 两阶段提取
  - 定位阶段返回正确行号
  - 提取阶段只处理指定区域
  - 超长文本处理成功

- [ ] 字段完整性检查
  - 正确识别缺失字段
  - 触发重新提取逻辑

- [ ] 增量爬取
  - 已存在且完整 → 跳过
  - 已存在但缺失 → 重新提取
  - 不存在 → 完整流程

- [ ] CSV 导出
  - 字段顺序正确
  - 其他作者正确展开
  - 只导出等级，不导出分数

- [ ] feedback 表
  - 表结构正确
  - 外键约束生效

### Non-Functional Requirements

- [ ] 性能
  - 100 条数据处理时间 < 90 分钟
  - API 调用符合速率限制

- [ ] 可靠性
  - 单条数据失败不影响整体
  - 错误日志完整

- [ ] 可维护性
  - 代码符合项目约定
  - 配置外置（YAML）
  - 日志级别适当

### Quality Gates

- [ ] 测试覆盖
  - 单元测试: 新增模块 100% 覆盖
  - 集成测试: 5 个核心场景通过

- [ ] 文档完整
  - 架构文档已更新
  - API 文档完整

- [ ] 代码审查
  - 符合项目代码风格
  - 无安全漏洞

---

## Success Metrics

1. **数据获取效率**
   - 单次搜索返回 > 100 条 PMID（vs 旧版 10-20 条）
   - DOI 转换成功率 > 95%

2. **提取成功率**
   - 提取成功率 > 80% (vs 旧版 33%)

3. **资源利用率**
   - 重复爬取率 < 5%（增量逻辑生效）

4. **数据质量**
   - 字段完整率 > 90%

---

## Dependencies & Prerequisites

### 外部依赖

- [ ] PubMed Entrez API 可用性
- [ ] NCBI ID Converter API 可用性
- [ ] Jina Reader API 额度充足
- [ ] GLM-5 API 额度充足

### 内部依赖

- [ ] PostgreSQL 16+ 已安装
- [ ] Python 3.11+ 环境
- [ ] 现有代码库可正常编译

### 配置依赖

- [ ] NCBI_EMAIL 环境变量
- [ ] NCBI_TOOL_NAME 环境变量
- [ ] GLM-5 API Key 有效

---

## Risk Analysis & Mitigation

### 高风险

1. **API 速率限制**
   - **风险**: PubMed Entrez 限制 3 requests/second
   - **缓解**: 实现速率限制器，批量处理

2. **DOI 缺失**
   - **风险**: 部分论文没有 DOI
   - **缓解**: DOI 允许 NULL，PMID 作为备用唯一标识

3. **提取失败率**
   - **风险**: 两阶段提取仍可能失败
   - **缓解**: 失败记录不入库，次日重试

### 中风险

4. **数据迁移失败**
   - **风险**: 清空数据后无法恢复
   - **缓解**: 提前备份数据库

5. **超长文本处理**
   - **风险**: 即使切片后仍超长
   - **缓解**: 多级切片，逐步缩小范围

### 低风险

6. **配置错误**
   - **风险**: 环境变量配置错误
   - **缓解**: 配置验证，默认值回退

---

## Resource Requirements

### 人力资源

- **开发**: 1人
- **测试**: 1人（可由开发兼任）
- **审查**: 1人

### 时间估算

- **Phase 1**: 数据库迁移 - 0.5 天
- **Phase 2**: 数据源层 - 1 天
- **Phase 3**: 提取层 - 1 天
- **Phase 4**: Pipeline - 1 天
- **Phase 5**: CSV 导出 - 0.5 天
- **Phase 6**: feedback - 0.5 天
- **测试**: 0.5 天
- **文档**: 0.5 天

**总计**: 5.5 天

### 基础设施

- PostgreSQL 数据库
- Python 虚拟环境
- API 调用额度（GLM-5, Jina）

---

## Future Considerations

### 可扩展性

1. **多数据源支持**
   - 当前仅 PubMed
   - 未来可扩展: OpenAlex, CNKI, Google Scholar

2. **评分策略优化**
   - 基于 feedback 数据自动调整权重（需人工确认）

3. **并行处理**
   - 当前串行处理
   - 未来可并行化提升效率

### 长期优化

1. **缓存机制**
   - 缓存常见作者的机构信息
   - 减少重复提取

2. **智能切片**
   - 基于 ML 预测关键信息位置
   - 减少定位阶段调用

3. **实时监控**
   - 提取成功率实时监控
   - API 调用统计

---

## Documentation Plan

### 需要更新的文档

- [x] docs/architecture/data_sources.md
- [x] docs/architecture/database_schema.md
- [x] docs/architecture/csv_output.md
- [x] docs/architecture/scoring_rules.md
- [x] docs/architecture/file_structure.md
- [x] docs/architecture/architecture_overview.md
- [x] docs/architecture/error_handling.md
- [x] docs/architecture/feedback_versioning.md

### 需要创建的文档

- [ ] docs/api/pubmed_entrez.md (PubMed API 使用说明)
- [ ] docs/api/ncbi_id_converter.md (ID Converter API 说明)
- [ ] docs/guides/incremental_crawling.md (增量爬取指南)

---

## Sources & References

### 内部引用

- 重构计划: docs/plans/2026-03-12-refactoring-plan.md
- 架构文档: docs/architecture/
- 需求文档: docs/plans/requirements_v4.md

### 外部引用

- PubMed Entrez API: https://www.ncbi.nlm.nih.gov/books/NBK25500/
- NCBI ID Converter: https://www.ncbi.nlm.nih.gov/pmc/tools/id-converter-api/
- Jina Reader: https://jina.ai/reader/
- GLM-5 API: https://open.bigmodel.cn/dev/api

### 相关工作

- 现有实现: src/crawlers/pubmed.py
- 现有实现: src/extractors/paper_extractor.py
- 现有实现: src/pipeline.py
- 现有实现: src/exporters/csv_exporter.py

---

## Implementation Checklist

### Phase 1: 数据库 (P0)
- [ ] 创建迁移脚本
- [ ] 新建 raw_markdown 表
- [ ] 修改 paper_leads 表
- [ ] 新建 feedback 表
- [ ] 运行迁移

### Phase 2: 数据源 (P0)
- [ ] 实现 PubMedEntrezClient
- [ ] 实现 NCBIIDConverter
- [ ] 速率限制器
- [ ] 单元测试

### Phase 3: 提取层 (P0)
- [ ] 实现 TwoStageExtractor
- [ ] 更新 PaperExtractor
- [ ] 集成测试

### Phase 4: Pipeline (P0)
- [ ] 重构 LeadPipeline
- [ ] 增量逻辑
- [ ] 飞书通知
- [ ] 集成测试

### Phase 5: CSV (P0)
- [ ] 更新 CSVExporter
- [ ] 其他作者展开
- [ ] 集成测试

### Phase 6: Feedback (P0)
- [ ] 创建 feedback 模型
- [ ] 外键关联
- [ ] (P2) 实现反馈收集

---

**计划状态**: ✅ 已完成
**创建时间**: 2026-03-12
**预计工期**: 5.5 天
**优先级**: P0 (全部)
