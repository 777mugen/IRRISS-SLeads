# System Architecture Overview

销售线索发现系统的核心架构：

## 数据流

```
关键词 → PubMed Entrez API → PMID列表 → NCBI ID Converter → DOI列表 → 
Jina Reader → Markdown → raw_markdown表 → 智谱批量API → 结构化JSON → 
paper_leads表 → 评分 → CSV导出 → 飞书通知
```

---

## Layers

### 1. Data Sources Layer
**论文数据**:
- PubMed (via Entrez API)
- NCBI ID Converter (PMID → DOI)

**招标数据**:
- 中国政府采购网
- 全国公共资源交易平台

### 2. Crawling Layer
**主力**: Jina Reader API
- DOI链接 → Markdown内容
- 自动剔除广告、脚本

**兜底**: Playwright
- 处理反爬站点
- 浏览器渲染

### 3. Storage Layer
**原始数据**:
- raw_markdown 表（DOI 主键）
- 存储 Markdown 原始内容

**结构化数据**:
- paper_leads 表（DOI 唯一标识）
- tender_leads 表

### 4. Extraction Layer（批量处理）

**批量处理模式**（推荐）:
- 从 raw_markdown 表读取未处理论文（processing_status = 'pending'）
- 构建 JSONL 文件（每行一个请求）
- 提交到智谱批量 API（https://open.bigmodel.cn/api/paas/v4/batches）
- 异步处理（10-30 分钟）
- 解析结果，更新 paper_leads

**模型**: GLM-4-Plus
- **优势**: 高吞吐量、低成本、无速率限制
- **适合**: 离线批量处理场景
- **max_tokens**: 4096

**实时 API 模式**（备用）:
- 两阶段提取：定位 + 提取
- 速率控制：高峰期30秒/请求，非高峰20秒/请求
- 429 自动重试

**Prompt 设计要点**:
- ✅ 明确不提取 References 部分
- ✅ 只提取正文中的通讯作者信息
- ✅ JSON 格式输出
- ✅ 字段缺失时返回 null

### 5. Scoring Layer
**7维度评分**（0-100分）:
- A. 信息完备度
- B. 预算状态（仅招标）
- C. 决策链条
- D. 匹配度
- E. 时效性
- F. 历史互动
- G. 机构类型

**等级映射**:
- A ≥ 80
- B = 65-79
- C = 50-64
- D < 50

### 6. Export Layer
**每日增量导出**:
- 新增 DOI
- 字段补齐的已有 DOI

**CSV字段**:
- DOI, 标题, 发表时间, 原文链接, 来源
- 通讯作者, 单位地址, 联系电话, 电子邮箱
- 其他作者信息（一人一行）
- 线索等级（A/B/C/D）

### 7. Notification Layer
**飞书通知**:
- 每日摘要
- 错误告警
- 字段更新确认

### 8. Feedback Loop
**销售反馈**:
- 5个维度（好/中/差）
- 线索准确性、需求匹配度、联系方式有效性、成交速度、成交价格

**数据回流**:
- 分析反馈数据
- 生成优化建议
- 人工审核后执行

---

## Key Design Principles

- ✅ **DOI 为唯一标识**: 通往全文的官方凭证
- ✅ **增量优先**: 已有DOI且字段完整 → 跳过
- ✅ **字段补齐**: 字段缺失 → 从 raw_markdown 重新提取
- ✅ **批量处理**: 离线批量提取，避免速率限制
- ✅ **处理状态跟踪**: raw_markdown.processing_status 跟踪处理进度
- ✅ **配置驱动**: 规则在 YAML 中管理
- ✅ **原始数据保留**: Markdown 可重新提取
- ✅ **可追溯**: 策略版本可回退
- ✅ **Agent Friendly**: 结构清晰，便于 AI 自动化开发

---

## 增量爬取逻辑

```python
if DOI 不存在:
    # 新线索
    获取 Markdown → 存储到 raw_markdown → processing_status='pending'
    
if DOI 存在 and processing_status == 'pending':
    # 批量提取
    加入下一个批处理任务 → 提交智谱 API → 等待结果
    
if DOI 存在 and processing_status == 'completed' and 字段缺失:
    # 补齐字段
    从 raw_markdown 重新提取 → 更新 paper_leads
    
if DOI 存在 and 字段完整:
    # 字段完整
    跳过
```

**必须字段**（任一缺失触发重新爬取）:
- 标题
- 发表时间
- 原文链接
- 来源
- 通讯作者
- 单位地址
- 联系电话
- 电子邮箱
