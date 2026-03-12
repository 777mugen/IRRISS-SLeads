# System Architecture Overview

销售线索发现系统的核心架构：

## 数据流

```
关键词 → PubMed Entrez API → PMID列表 → NCBI ID Converter → DOI列表 → 
Jina Reader → Markdown → 存储 → GLM-5提取 → 结构化JSON → 评分 → 入库 → CSV导出 → 飞书通知
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

### 4. Extraction Layer
**两阶段提取**:
1. 定位阶段：搜索关键词（Correspondence, Email, Affiliation）
2. 提取阶段：提取指定区域的结构化字段

**模型**: GLM-5
- 速率控制：高峰期30秒/请求，非高峰20秒/请求
- 429 自动重试

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
- ✅ **字段补齐**: 字段缺失 → 重新提取
- ✅ **两阶段提取**: 先定位再提取，避免超长上下文
- ✅ **配置驱动**: 规则在 YAML 中管理
- ✅ **原始数据保留**: Markdown 可重新提取
- ✅ **可追溯**: 策略版本可回退
- ✅ **Agent Friendly**: 结构清晰，便于 AI 自动化开发

---

## 增量爬取逻辑

```python
if DOI 不存在:
    # 新线索
    获取 Markdown → 提取 → 评分 → 入库
elif DOI 存在 and 字段缺失:
    # 补齐字段
    从 raw_markdown 重新提取 → 更新 → 发送通知
else:
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
