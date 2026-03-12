# SLeads 系统重构计划

## 一、架构变更总览

### 核心变更
1. **数据源层**：Jina Search → PubMed Entrez API + NCBI ID Converter API
2. **存储层**：新增 raw_markdown 表，DOI 作为 UNIQUE 约束
3. **提取层**：两次 GLM 调用（定位 + 提取）
4. **字段层**：移除 keywords_matched，调整字段定义
5. **反馈层**：新建 feedback 表

---

## 二、详细实现步骤

### Phase 1: 数据库重构 (Database Restructuring)

#### 1.1 新增 raw_markdown 表
```sql
CREATE TABLE raw_markdown (
    id SERIAL PRIMARY KEY,
    doi VARCHAR UNIQUE NOT NULL,
    pmid VARCHAR,
    markdown_content TEXT NOT NULL,
    source_url VARCHAR NOT NULL,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 1.2 修改 paper_leads 表
```sql
-- 移除字段
ALTER TABLE paper_leads DROP COLUMN keywords_matched;

-- 新增字段
ALTER TABLE paper_leads ADD COLUMN source VARCHAR(50) DEFAULT 'PubMed';
ALTER TABLE paper_leads ADD COLUMN article_url VARCHAR;  -- https://doi.org/[DOI]

-- 修改 DOI 约束
ALTER TABLE paper_leads ADD CONSTRAINT unique_doi UNIQUE (doi);

-- 修改 all_authors 字段注释（JSON 格式，但 CSV 导出时展开）
COMMENT ON COLUMN paper_leads.all_authors IS 'JSON array: [{name, institution, email, phone}]';
```

#### 1.3 新增 feedback 表
```sql
CREATE TABLE feedback (
    id SERIAL PRIMARY KEY,
    paper_lead_id INTEGER REFERENCES paper_leads(id),
    
    -- 5个反馈维度（好/中/差）
    accuracy VARCHAR(10),  -- 线索准确性
    demand_match VARCHAR(10),  -- 需求匹配度
    contact_validity VARCHAR(10),  -- 联系方式有效性
    deal_speed VARCHAR(10),  -- 成交速度
    deal_price VARCHAR(10),  -- 成交价格
    
    notes TEXT,  -- 销售备注
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 1.4 字段定义更新
```
必须字段（任意缺失触发重新爬取）：
- 标题 (title)
- 发表时间 (published_at)
- 原文链接 (article_url) = https://doi.org/[DOI]
- 来源 (source) = 'PubMed' (动态判断)
- 通讯作者 (name)
- 单位地址 (address)
- 联系电话 (phone)
- 电子邮箱 (email)
```

---

### Phase 2: 数据源层重构 (Data Source Layer)

#### 2.1 新增 PubMed Entrez API 客户端
**文件**: `src/crawlers/pubmed_entrez.py`

```python
class PubMedEntrezClient:
    """
    PubMed Entrez API 客户端
    官方文档: https://www.ncbi.nlm.nih.gov/books/NBK25500/
    """
    
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
    ) -> list[str]:
        """
        搜索论文，返回 PMID 列表
        
        API: esearch.fcgi
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
        pmids = data.get("esearchresult", {}).get("idlist", [])
        
        return pmids
    
    async def fetch_details(self, pmids: list[str]) -> list[dict]:
        """
        获取论文详情（包括 DOI）
        
        API: efetch.fcgi
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
        
        # 解析 XML，提取 DOI
        # 返回 [{pmid, doi, title, abstract, ...}, ...]
```

#### 2.2 新增 NCBI ID Converter API 客户端
**文件**: `src/crawlers/ncbi_id_converter.py`

```python
class NCBIIDConverter:
    """
    NCBI ID Converter API 客户端
    官方文档: https://www.ncbi.nlm.nih.gov/pmc/tools/id-converter-api/
    """
    
    BASE_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=30.0)
    
    async def convert_pmids_to_dois(self, pmids: list[str]) -> dict[str, str]:
        """
        批量转换 PMID → DOI
        
        Args:
            pmids: PMID 列表
            
        Returns:
            {pmid: doi, ...}
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

---

### Phase 3: 提取层重构 (Extraction Layer)

#### 3.1 新增两阶段提取策略
**文件**: `src/extractors/two_stage_extractor.py`

```python
class TwoStageExtractor:
    """两阶段提取：先定位，再提取"""
    
    async def extract(self, markdown: str) -> dict:
        # Stage 1: 定位关键信息位置
        keywords_prompt = """
在以下 Markdown 文本中，找到以下关键词出现的位置：
- Correspondence / Corresponding Author
- Affiliation
- Email / E-mail
- Phone / Telephone

返回 JSON 格式：
{
  "correspondence_start": <行号>,
  "correspondence_end": <行号>,
  "affiliation_start": <行号>,
  "email_start": <行号>,
  "phone_start": <行号>
}

文本内容：
{markdown[:5000]}
"""
        
        locations = await self.llm.call(keywords_prompt)
        
        # Stage 2: 提取指定区域内容
        extract_prompt = f"""
从以下文本片段中提取通讯作者信息：

通讯作者区域：
{markdown[locations['correspondence_start']:locations['correspondence_end']]}

返回 JSON 格式：
{{
  "name": "通讯作者姓名",
  "email": "邮箱",
  "phone": "电话",
  "institution": "单位",
  "address": "地址"
}}
"""
        
        author_info = await self.llm.call(extract_prompt)
        
        return author_info
```

---

### Phase 4: Pipeline 重构 (Pipeline Refactoring)

#### 4.1 新的执行流程
**文件**: `src/pipeline.py`

```python
class LeadPipeline:
    """重构后的 Pipeline"""
    
    async def process_paper(self, pmid: str, doi: str = None):
        """
        处理单篇论文
        
        流程：
        1. 检查是否已存在且字段完整
        2. 如果需要爬取：
           a. 构建 DOI 链接
           b. 调用 Jina Reader
           c. 存储 Markdown 到 raw_markdown 表
           d. 两阶段提取
           e. 评分
           f. 入库
        3. 如果字段完整，跳过
        """
        
        # Step 1: 检查是否存在
        existing = await self.check_existing(doi or pmid)
        
        if existing and self.is_complete(existing):
            self.logger.info(f"跳过 {pmid}: 字段完整")
            return None
        
        # Step 2: 获取 DOI（如果没有）
        if not doi:
            doi = await self.convert_pmid_to_doi(pmid)
        
        # Step 3: 获取 Markdown
        article_url = f"https://doi.org/{doi}"
        markdown = await self.jina_reader.read(article_url)
        
        # Step 4: 存储 Markdown
        await self.save_raw_markdown(doi, pmid, markdown, article_url)
        
        # Step 5: 两阶段提取
        extracted = await self.two_stage_extract(markdown)
        
        # Step 6: 评分
        score, grade = await self.scorer.score(extracted)
        
        # Step 7: 入库
        lead = {
            'pmid': pmid,
            'doi': doi,
            'title': extracted['title'],
            'published_at': extracted['published_at'],
            'article_url': article_url,
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
        return all(required)
```

---

### Phase 5: CSV 导出重构 (CSV Export Refactoring)

#### 5.1 导出逻辑调整
**文件**: `src/exporters/csv_exporter.py`

```python
class CSVExporter:
    """CSV 导出器（重构版）"""
    
    def export_incremental(self, date: date) -> Path:
        """
        导出增量数据（新增 + 更新）
        """
        leads = await self.get_leads_by_date(date)
        
        csv_rows = []
        for lead in leads:
            # 基础字段
            row = {
                'DOI': lead.doi,
                '标题': lead.title,
                '发表时间': str(lead.published_at),
                '原文链接': lead.article_url,
                '来源': lead.source,
                '通讯作者': lead.name,
                '单位地址': lead.address,
                '联系电话': lead.phone,
                '电子邮箱': lead.email,
                '线索等级': lead.grade,  # 只暴露等级，不暴露分数
            }
            
            # 其他作者信息展开（一人一行）
            if lead.all_authors:
                authors = json.loads(lead.all_authors)
                author_lines = []
                for author in authors:
                    author_lines.append(
                        f"{author.get('name', '')}, "
                        f"{author.get('institution', '')}, "
                        f"{author.get('email', '')}, "
                        f"{author.get('phone', '')}"
                    )
                row['其他作者信息'] = "\n".join(author_lines)
            
            csv_rows.append(row)
        
        # 写入 CSV
        return self.write_csv(csv_rows, date)
```

---

## 三、数据库迁移 SQL

```sql
-- 1. 创建 raw_markdown 表
CREATE TABLE raw_markdown (
    id SERIAL PRIMARY KEY,
    doi VARCHAR UNIQUE NOT NULL,
    pmid VARCHAR,
    markdown_content TEXT NOT NULL,
    source_url VARCHAR NOT NULL,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 修改 paper_leads 表
ALTER TABLE paper_leads DROP COLUMN IF EXISTS keywords_matched;
ALTER TABLE paper_leads ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'PubMed';
ALTER TABLE paper_leads ADD COLUMN IF NOT EXISTS article_url VARCHAR;
ALTER TABLE paper_leads ADD CONSTRAINT unique_doi UNIQUE (doi);

-- 3. 创建 feedback 表
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

-- 4. 创建索引
CREATE INDEX idx_raw_markdown_doi ON raw_markdown(doi);
CREATE INDEX idx_paper_leads_source ON paper_leads(source);
CREATE INDEX idx_feedback_paper_lead_id ON feedback(paper_lead_id);
```

---

## 四、实现优先级

### P0 (必须完成)
1. ✅ 数据库迁移 SQL
2. ✅ PubMed Entrez API 客户端
3. ✅ NCBI ID Converter API 客户端
4. ✅ Pipeline 重构（增量逻辑）
5. ✅ 字段完整性检查

### P1 (重要)
6. ✅ 两阶段提取器
7. ✅ CSV 导出器重构
8. ✅ raw_markdown 存储逻辑

### P2 (可延后)
9. ⏳ feedback 表相关逻辑
10. ⏳ 销售反馈界面

---

## 五、风险与注意事项

### 5.1 API 限制
- **PubMed Entrez**: 3 requests/second (无 API Key)
- **解决方案**: 实现速率限制器

### 5.2 DOI 缺失
- 少数论文可能没有 DOI
- **解决方案**: DOI 允许 NULL，但作为 UNIQUE 约束

### 5.3 数据迁移
- 现有 7 条数据需要迁移
- **解决方案**: 编写迁移脚本，补充缺失字段

---

## 六、测试计划

### 6.1 单元测试
- [ ] PubMed Entrez API 调用
- [ ] NCBI ID Converter API 调用
- [ ] 字段完整性检查
- [ ] 两阶段提取

### 6.2 集成测试
- [ ] 完整 Pipeline 测试（10 条数据）
- [ ] 增量爬取测试
- [ ] CSV 导出测试

### 6.3 回归测试
- [ ] 确保现有功能不受影响
