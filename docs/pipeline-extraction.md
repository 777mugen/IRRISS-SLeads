# Paper Extraction Pipeline 文档

**创建时间**: 2026-03-15  
**用途**: 为 AI Agent 提供完整的论文提取流程文档

---

## 📋 Pipeline 概述

**目标**: 从 PubMed 搜索论文，提取作者信息，保存到数据库

**流程**:
```
PubMed API 搜索
    ↓
获取 PMID 列表 (PubMedEntrezClient)
    ↓
获取论文详情 (PMID, DOI, Title, Abstract)
    ↓
Jina Reader 获取全文 Markdown
    ↓
Zhipu 批处理 API 提取作者信息
    ↓
保存到数据库 (raw_markdown + paper_leads)
```

---

## 🔧 核心组件

### 1. PubMed API Client
**文件**: `src/crawlers/pubmed_entrez.py`

**类**: `PubMedEntrezClient`

**主要方法**:
- `search(query, max_results, date_range)` - 搜索论文，返回 PMID 列表
- `fetch_details(pmids)` - 获取论文详情
- `search_and_fetch(query, max_results, date_range)` - 一步到位

**速率限制**:
- 无 API Key: 3 requests/second
- 有 API Key: 10 requests/second

**配置**:
- Email: Shane@irriss.com
- Tool: IRRISS-SLeads

### 2. Jina Reader Client
**文件**: `src/crawlers/jina_client.py`

**用途**: 获取论文全文 Markdown

**方法**: `read_paper(url)`

**支持的 URL 格式**:
- `https://doi.org/{doi}`
- `https://pubmed.ncbi.nlm.nih.gov/{pmid}/`

### 3. Zhipu Batch Client
**文件**: `src/llm/batch_client.py`

**用途**: 批量提取作者信息

**方法**:
- `create_batch(task_file, description)` - 创建批处理任务
- `get_batch_status(batch_id)` - 查询状态
- `download_results(batch_id)` - 下载结果

**模型**: glm-4-plus

### 4. Extraction Pipeline
**文件**: `src/pipeline.py`

**类**: `LeadPipeline`

**主要方法**:
- `process_paper_with_doi(pmid, doi, markdown)` - 处理单篇论文
- `save_raw_markdown(doi, pmid, markdown, source_url)` - 保存 Markdown
- `save_paper_lead(lead_data)` - 保存线索

---

## 📊 关键词配置

**文件**: `config/keywords.yaml`

**结构**:
```yaml
english:
  core:
    - "Multiplex Immunofluorescence"
    - "mIF"
    - "TSA"
    - "Spatial Proteomics"
    ...
  equipment:
    - "Confocal Microscopy"
    - "Olympus"
    - "ZEISS"
    ...

chinese:
  core:
    - "多重免疫荧光"
    - "免疫荧光"
    ...
```

---

## 🚀 执行脚本

### 脚本 1: extract_1000_papers.py
**路径**: `scripts/extract_1000_papers.py`

**功能**: 完整提取流程（1000 篇论文）

**执行方式**:
```bash
# 前台运行（会超时）
python scripts/extract_1000_papers.py

# 后台运行（推荐）
nohup python scripts/extract_1000_papers.py > logs/extract_1000.log 2>&1 &

# 监控进度
tail -f logs/extract_1000.log
cat tmp/extraction_progress_*.json
```

**输出文件**:
- `tmp/extraction_progress_{timestamp}.json` - 进度文件（每 10 篇更新）
- `tmp/extraction_stats_{timestamp}.json` - 统计文件
- `tmp/batch_tasks_{timestamp}.jsonl` - 批处理任务文件

**预估时间**:
- 搜索论文: 10-15 分钟
- 获取全文: 30-60 分钟（1000 次 Jina API）
- 提交批处理: 1-2 分钟
- **总计**: 40-80 分钟

### 脚本 2: test_extract_10_papers.py
**路径**: `scripts/test_extract_10_papers.py`

**功能**: 快速测试（10 篇论文）

**执行方式**:
```bash
python scripts/test_extract_10_papers.py
```

**用时**: 约 30 秒

---

## 📈 进度监控

### 方法 1: 查看日志文件
```bash
# 实时查看日志
tail -f logs/extract_1000.log

# 查看进度文件
cat tmp/extraction_progress_*.json | jq .
```

### 方法 2: 检查批处理状态
```bash
# 查询 Zhipu 批处理状态
python scripts/check_batch_status.py {batch_id}
```

### 方法 3: 查看 Web Dashboard
访问: http://localhost:8000/batch/monitor

---

## 🔍 超时问题分析与解决

### 问题 1: 执行超时
**现象**: 脚本在运行中被 SIGTERM 终止

**原因**:
1. **前台运行**: 直接执行脚本，终端超时或网络断开会导致中断
2. **执行时间过长**: 1000 篇论文需要 40-80 分钟
3. **没有后台守护**: 没有使用 nohup 或 screen

**解决方案**:
```bash
# 方案 A: 使用 nohup（推荐）
nohup python scripts/extract_1000_papers.py > logs/extract_1000.log 2>&1 &

# 方案 B: 使用 screen
screen -S extraction
python scripts/extract_1000_papers.py
# Ctrl+A, D 分离

# 方案 C: 使用 tmux
tmux new -s extraction
python scripts/extract_1000_papers.py
# Ctrl+B, D 分离
```

### 问题 2: API 速率限制
**现象**: 请求被拒绝或延迟

**原因**:
- PubMed API: 3 requests/second（无 Key）
- Jina API: 有速率限制

**解决方案**:
```python
# 已在代码中实现速率限制
await asyncio.sleep(0.5)  # PubMed
await asyncio.sleep(1.0)  # Jina
```

### 问题 3: 内存占用
**现象**: 处理大量论文时内存不足

**原因**: 一次性加载所有论文数据

**解决方案**:
```python
# 使用流式处理（已在脚本中实现）
# 每 10 篇保存一次进度
if i % 10 == 0:
    save_progress()
```

---

## ⚡ 性能优化建议

### 1. 分批处理
```bash
# 分 10 批，每批 100 篇
for i in {1..10}; do
    python scripts/extract_batch_$i.py
    sleep 300  # 休息 5 分钟
done
```

### 2. 断点续传
```python
# 从进度文件恢复
if progress_file.exists():
    start_from = load_progress()
```

### 3. 并发优化
```python
# 使用 asyncio.gather 并发获取全文
tasks = [fetch_paper(doi) for doi in dois]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

### 4. 缓存机制
```python
# 检查已处理的 DOI
if doi in processed_dois:
    continue
```

---

## 🗄️ 数据库模型

### raw_markdown 表
**用途**: 存储论文全文 Markdown

**字段**:
- `id` - 主键
- `doi` - DOI（唯一）
- `pmid` - PMID
- `markdown_content` - Markdown 内容
- `source_url` - 来源 URL
- `processing_status` - 处理状态 (pending/processing/completed/failed)
- `batch_id` - 批处理 ID
- `fetched_at` - 获取时间
- `created_at` - 创建时间

### paper_leads 表
**用途**: 存储提取的作者信息

**字段**:
- `id` - 主键
- `doi` - DOI
- `pmid` - PMID
- `title` - 标题
- `published_at` - 发表日期
- `article_url` - 论文链接
- `source` - 来源
- `name` - 通讯作者姓名
- `email` - 邮箱
- `phone` - 电话
- `institution` - 机构
- `address` - 地址
- `score` - 评分
- `grade` - 等级 (A/B/C/D/E)
- `keywords_matched` - 匹配的关键词
- `feedback_status` - 反馈状态
- `created_at` - 创建时间

---

## 🎯 使用建议

### 快速开始
```bash
# 1. 测试 10 篇论文（30 秒）
python scripts/test_extract_10_papers.py

# 2. 提取 100 篇论文（5-10 分钟）
# 修改 extract_1000_papers.py 中的 target_count = 100
nohup python scripts/extract_1000_papers.py > logs/extract_100.log 2>&1 &

# 3. 提取 1000 篇论文（40-80 分钟）
nohup python scripts/extract_1000_papers.py > logs/extract_1000.log 2>&1 &
```

### 监控进度
```bash
# 查看日志
tail -f logs/extract_1000.log

# 查看进度
cat tmp/extraction_progress_*.json | jq .

# 查看 Web Dashboard
open http://localhost:8000/batch/monitor
```

### 处理结果
```bash
# 批处理完成后，下载结果
python scripts/process_batch_results.py {batch_id}
```

---

## 📝 注意事项

### 1. API 限制
- PubMed API: 需要遵守速率限制（3 req/s）
- Jina API: 有调用限制
- Zhipu API: 批处理需要时间（1000 篇约 1-2 小时）

### 2. 数据质量
- 部分论文无 DOI（会跳过）
- 部分论文全文获取失败（会记录错误）
- 提取结果需要人工验证

### 3. 系统要求
- Python 3.8+
- PostgreSQL 数据库
- 网络连接稳定

### 4. 备份策略
- 进度文件自动保存（每 10 篇）
- 可从进度文件恢复
- 建议定期备份数据库

---

## 🔗 相关文档

- [PubMed API 文档](https://www.ncbi.nlm.nih.gov/books/NBK25500/)
- [Jina Reader 文档](https://jina.ai/reader/)
- [Zhipu API 文档](https://open.bigmodel.cn/dev/api)
- [Pipeline 架构文档](../../src/pipeline.py)
- [数据库模型文档](../../src/db/models.py)

---

## 📞 故障排查

### 问题: PubMed API 返回空结果
**解决**: 检查关键词格式，使用双引号包裹

### 问题: Jina Reader 获取失败
**解决**: 检查 DOI 是否有效，部分论文需要订阅

### 问题: Zhipu 批处理失败
**解决**: 检查任务文件格式，确保 JSON 正确

### 问题: 数据库连接失败
**解决**: 检查 PostgreSQL 是否运行，检查连接配置

---

**最后更新**: 2026-03-15  
**维护者**: AI Agent  
**版本**: 1.0
