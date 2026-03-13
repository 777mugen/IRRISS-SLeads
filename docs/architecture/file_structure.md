# 项目文件结构

src/
crawlers/
  __init__.py
  base.py
  jina_client.py           # Jina Reader/Search API 客户端
  pubmed_entrez.py         # PubMed Entrez API 客户端（新增）
  ncbi_id_converter.py     # NCBI ID Converter API 客户端（新增）
  playwright_client.py     # Playwright 兜底爬虫
  content_fetcher.py       # 统一内容获取接口
  collectors.py            # URL 收集器
  tender.py                # 招标爬虫
  pubmed.py                # PubMed 爬虫（旧版，保留）

extractors/
  __init__.py
  base.py                 # 基础提取器
  paper_extractor.py      # 论文提取器（GLM-5）
  tender_extractor.py     # 招标提取器
  two_stage_extractor.py  # 两阶段提取器（新增）

processors/
  url_deduplicator.py      # URL 去重
  batch_processor.py       # 批量处理器（构建 JSONL）
  batch_result_parser.py   # 批量结果解析器

prompts/
  batch_extraction.py      # 批量提取 Prompt（v2）

llm/
  rate_limiter.py          # GLM-5 速率控制
  extractor.py             # LLM 提取器
  batch_client.py          # 智谱批量 API 客户端

batch/
  pipeline_batch.py        # 批量处理 Pipeline

scoring/
  paper_scorer.py          # 论文评分
  tender_scorer.py         # 招标评分

exporters/
  csv_exporter.py          # CSV 导出

notifiers/
  __init__.py
  feishu.py                # 飞书通知

db/
  models.py                # 数据库模型
  utils.py                 # 数据库工具

scheduler/
  scheduler.py             # 定时任务

pipeline.py                # 主 Pipeline

config/
  keywords.yaml
  sources.yaml
  scoring_paper.yaml
  scoring_tender.yaml
  scheduler.yaml

tests/

output/
  paper_leads/
  tender_leads/

logs/

.env
.env.example
