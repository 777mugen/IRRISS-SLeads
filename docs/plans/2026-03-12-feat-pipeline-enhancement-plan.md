---
title: SLeads Pipeline Enhancement - Rate Control & Complete Workflow
type: feat
status: active
date: 2026-03-12
---

# SLeads Pipeline Enhancement - Rate Control & Complete Workflow

## Overview

整合今天讨论的所有待实现功能，完善 SLeads 管道的完整工作流程。

## 已完成的工作（不在本计划范围）

| 功能 | 状态 | 提交 |
|------|------|------|
| 调度器 (run_daily_task, run_full_export) | ✅ 完成 | `5e20fb8` |
| 两种收集模式 (Search/Library) | ✅ 完成 | `0a73f8a` |
| PMID/DOI/all_authors 字段 | ✅ 完成 | `1c8d749` |
| CSV 导出 15 列字段 | ✅ 完成 | `1c8d749` |
| Playwright Fallback 计划 | ✅ 计划完成 | `32701cc` |

## 本计划范围

1. GLM-5 速率控制
2. 招标爬虫实现
3. 飞书通知配置
4. 完整流程测试

## Phase 1: GLM-5 速率控制

### Problem

当前 LLM 提取时频繁触发 429 限流：
```
HTTP Request: POST https://open.bigmodel.cn/api/paas/v4/chat/completions "HTTP/1.1 429 Too Many Requests"
```

### API 限制分析

| 套餐 | 每 5 小时限额 | GLM-5 消耗系数 |
|------|--------------|----------------|
| Lite | ~80 次 | 高峰期 3x，非高峰期 2x |
| Pro | ~400 次 | 高峰期 3x，非高峰期 2x |
| Max | ~1600 次 | 高峰期 3x，非高峰期 2x |

**高峰期**: 14:00～18:00 (UTC+8)

### Solution

**文件**: `src/llm/rate_limiter.py`

```python
"""
LLM Rate Limiter for GLM-5 API.
GLM-5 API 速率限制器。
"""

import asyncio
import time
from datetime import datetime, time as dt_time
from typing import Optional
from src.logging_config import get_logger

class GLMRateLimiter:
    """
    GLM-5 速率限制器
    
    根据时段自动调整请求间隔：
    - 高峰期 (14:00-18:00): 30 秒/请求
    - 非高峰期: 20 秒/请求
    """
    
    # 时段配置
    PEAK_START = dt_time(14, 0)   # 高峰期开始
    PEAK_END = dt_time(18, 0)     # 高峰期结束
    
    # 间隔配置
    PEAK_INTERVAL = 30.0          # 高峰期间隔（秒）
    OFF_PEAK_INTERVAL = 20.0      # 非高峰期间隔（秒）
    
    def __init__(self):
        self.logger = get_logger()
        self._last_request_time: float = 0
        self._lock = asyncio.Lock()
    
    def _is_peak_hour(self) -> bool:
        """检查当前是否为高峰期"""
        now = datetime.now().time()
        return self.PEAK_START <= now <= self.PEAK_END
    
    def _get_interval(self) -> float:
        """获取当前应使用的间隔"""
        return self.PEAK_INTERVAL if self._is_peak_hour() else self.OFF_PEAK_INTERVAL
    
    async def acquire(self):
        """
        获取请求许可
        
        会自动等待直到满足速率限制
        """
        async with self._lock:
            interval = self._get_interval()
            elapsed = time.time() - self._last_request_time
            
            if elapsed < interval:
                wait_time = interval - elapsed
                self.logger.debug(
                    f"速率限制: 等待 {wait_time:.1f} 秒 "
                    f"(高峰期={'是' if self._is_peak_hour() else '否'})"
                )
                await asyncio.sleep(wait_time)
            
            self._last_request_time = time.time()
    
    def get_stats(self) -> dict:
        """获取速率限制器状态"""
        return {
            'is_peak_hour': self._is_peak_hour(),
            'current_interval': self._get_interval(),
            'last_request': self._last_request_time,
            'seconds_since_last': time.time() - self._last_request_time
        }
```

**修改**: `src/llm/client.py`

```python
from src.llm.rate_limiter import GLMRateLimiter

class ZAIClient:
    def __init__(self, ...):
        ...
        self.rate_limiter = GLMRateLimiter()
    
    async def chat(self, prompt: str, ...) -> str:
        # 应用速率限制
        await self.rate_limiter.acquire()
        
        # 原有逻辑
        response = await self._client.post(...)
        ...
```

### Acceptance Criteria

- [x] `GLMRateLimiter` 类实现
- [x] 高峰期 (14:00-18:00) 30 秒/请求
- [x] 非高峰期 20 秒/请求
- [x] 集成到 `ZAIClient`
- [x] 添加重试逻辑（429 时自动重试）
- [x] 日志记录等待时间

---

## Phase 2: 招标爬虫实现

### Problem

当前只有论文爬虫，缺少招标信息爬取功能。

### Data Sources

| 数据源 | URL | 说明 |
|--------|-----|------|
| 中国政府采购网 | http://www.ccgp.gov.cn | 官方招标公告 |
| 中国招标投标公共服务平台 | http://www.cebpubservice.com | 综合平台 |

### Solution

**文件**: `src/crawlers/tender.py`

```python
"""
Tender (招标) crawler.
招标爬虫。
"""

from datetime import date, datetime, timedelta
from typing import Optional
from urllib.parse import quote_plus

from src.crawlers.jina_client import JinaClient
from src.config import config
from src.logging_config import get_logger

class TenderCrawler:
    """
    招标爬虫
    
    使用 Jina Search 搜索招标信息
    支持多个招标平台
    """
    
    # 招标关键词
    KEYWORDS = [
        "免疫荧光",
        "mIF",
        "病理",
        "病理诊断",
        "医学检测",
    ]
    
    def __init__(self):
        self.logger = get_logger()
        self.jina = JinaClient()
        self.keywords = config.tender_keywords or self.KEYWORDS
    
    async def search_tenders(
        self, 
        days_back: int = 7,
        max_results: int = 20
    ) -> list[dict]:
        """
        搜索招标信息
        
        Args:
            days_back: 回溯天数
            max_results: 最大结果数
            
        Returns:
            招标公告列表
        """
        all_results = []
        
        for keyword in self.keywords:
            query = f'"{keyword}" 招标 公告'
            
            self.logger.info(f"搜索招标: {query}")
            
            urls = await self.jina.search(
                query=query,
                max_results=max_results // len(self.keywords),
                site=None  # 不限制站点
            )
            
            for url in urls:
                all_results.append({
                    'url': url,
                    'keyword': keyword,
                    'status': 'pending'
                })
        
        # 去重
        seen = set()
        unique_results = []
        for r in all_results:
            if r['url'] not in seen:
                seen.add(r['url'])
                unique_results.append(r)
        
        self.logger.info(f"搜索到 {len(unique_results)} 条招标信息")
        return unique_results[:max_results]
    
    async def fetch_tender(self, url: str) -> dict:
        """
        获取招标详情
        
        Args:
            url: 招标公告 URL
            
        Returns:
            招标详情
        """
        try:
            content = await self.jina.read(url)
            return {
                'url': url,
                'content': content,
                'status': 'success'
            }
        except Exception as e:
            self.logger.error(f"获取招标失败 ({url}): {e}")
            return {
                'url': url,
                'content': '',
                'status': 'failed',
                'error': str(e)
            }
    
    async def run(
        self,
        days_back: int = 7,
        max_tenders: int = 20
    ) -> list[dict]:
        """
        运行招标爬虫
        
        Args:
            days_back: 回溯天数
            max_tenders: 最大数量
            
        Returns:
            招标列表（含内容）
        """
        # 搜索
        tenders = await self.search_tenders(days_back, max_tenders)
        
        # 获取内容
        for tender in tenders:
            result = await self.fetch_tender(tender['url'])
            tender.update(result)
        
        successful = [t for t in tenders if t['status'] == 'success']
        self.logger.info(f"成功获取 {len(successful)}/{len(tenders)} 条招标")
        
        return tenders
    
    async def close(self):
        await self.jina.close()
```

### Acceptance Criteria

- [x] `TenderCrawler` 类实现
- [x] 支持多关键词搜索
- [x] URL 去重
- [ ] 集成到 `run_daily_task`
- [ ] 测试：搜索 "免疫荧光 招标" 返回结果

---

## Phase 3: 飞书通知配置

### Problem

定时任务完成后需要通知用户。

### Solution

**文件**: `src/notifiers/feishu.py`

```python
"""
Feishu notification client.
飞书通知客户端。
"""

import httpx
from typing import Optional
from src.config import config
from src.logging_config import get_logger

class FeishuNotifier:
    """
    飞书机器人通知
    
    使用 Webhook 发送消息到飞书群
    """
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or config.feishu_webhook
        self.logger = get_logger()
        self._client = httpx.AsyncClient(timeout=10.0)
    
    async def send_text(self, text: str) -> bool:
        """
        发送文本消息
        
        Args:
            text: 消息内容
            
        Returns:
            是否成功
        """
        if not self.webhook_url:
            self.logger.warning("飞书 Webhook 未配置")
            return False
        
        payload = {
            "msg_type": "text",
            "content": {
                "text": text
            }
        }
        
        try:
            response = await self._client.post(
                self.webhook_url,
                json=payload
            )
            response.raise_for_status()
            self.logger.info("飞书通知发送成功")
            return True
        except Exception as e:
            self.logger.error(f"飞书通知发送失败: {e}")
            return False
    
    async def send_daily_summary(self, stats: dict) -> bool:
        """
        发送每日任务摘要
        
        Args:
            stats: {
                'papers_found': int,
                'papers_processed': int,
                'tenders_found': int,
                'leads_exported': int,
                'duration_seconds': float
            }
        """
        text = f"""📊 每日线索采集完成

📄 论文: 发现 {stats.get('papers_found', 0)} 篇，处理 {stats.get('papers_processed', 0)} 篇
📋 招标: 发现 {stats.get('tenders_found', 0)} 条
📤 导出: {stats.get('leads_exported', 0)} 条线索
⏱️ 耗时: {stats.get('duration_seconds', 0):.1f} 秒

时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
        return await self.send_text(text)
    
    async def close(self):
        await self._client.aclose()
```

### Configuration

**文件**: `.env`

```bash
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
```

### Acceptance Criteria

- [x] `FeishuNotifier` 类实现
- [x] 支持文本消息
- [x] 支持每日摘要
- [x] 配置项 `FEISHU_WEBHOOK`
- [ ] 集成到 `run_daily_task`
- [ ] 测试：发送测试消息到群

---

## Phase 4: 完整流程测试

### Test Scenarios

**文件**: `tests/test_full_pipeline.py`

```python
"""
Full pipeline integration test.
完整管道集成测试。
"""

import asyncio
from src.crawlers.collectors import MultiModeCollector
from src.crawlers.content_fetcher import ContentFetcher
from src.pipeline import LeadPipeline
from src.exporters.csv_exporter import CSVExporter
from src.processors.url_deduplicator import URLDeduplicator

async def test_full_pipeline():
    """测试完整流程"""
    
    # 1. 多模式收集 URL
    collector = MultiModeCollector(
        keywords=["mIF", "immunofluorescence"],
        max_results_per_mode=5
    )
    merged_urls = await collector.collect_all()
    print(f"✅ 收集到 {len(merged_urls)} 个唯一 URL")
    
    # 2. 去重
    deduplicator = URLDeduplicator()
    unique_urls = deduplicator.deduplicate([u['url'] for u in merged_urls])
    print(f"✅ 去重后 {len(unique_urls)} 个 URL")
    
    # 3. 获取内容（带 Fallback）
    fetcher = ContentFetcher(enable_playwright=True)
    contents = []
    for url_info in merged_urls[:3]:  # 测试前 3 个
        result = await fetcher.fetch(url_info['url'])
        contents.append(result)
        print(f"  {result['source']}: {url_info['url'][:50]}...")
    await fetcher.close()
    print(f"✅ 获取内容完成")
    
    # 4. LLM 提取（带速率控制）
    pipeline = LeadPipeline()
    for content in contents:
        if content['success']:
            result = await pipeline.process_paper(
                content['url'],
                content['content']
            )
            if result:
                print(f"  ✅ 提取: {result.get('title', 'N/A')[:30]}...")
    await pipeline.close()
    print(f"✅ LLM 提取完成")
    
    # 5. CSV 导出
    exporter = CSVExporter()
    # ... 导出逻辑
    print(f"✅ CSV 导出完成")

if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
```

### Acceptance Criteria

- [ ] 完整流程测试脚本
- [ ] 覆盖：收集 → 去重 → 获取 → 提取 → 评分 → 导出
- [ ] 测试通过（至少 3 篇论文端到端）
- [ ] 生成有效 CSV

---

## Implementation Timeline

| Phase | 内容 | 估计时间 |
|-------|------|----------|
| Phase 1 | GLM-5 速率控制 | 1 小时 |
| Phase 2 | 招标爬虫 | 2 小时 |
| Phase 3 | 飞书通知 | 1 小时 |
| Phase 4 | 完整测试 | 1 小时 |

**总计**: 约 5 小时

## Dependencies

| 依赖 | 版本 | Phase |
|------|------|-------|
| httpx | >= 0.25.0 | 3 (飞书) |

## Success Metrics

1. **速率控制**: 不再触发 429 错误
2. **招标爬虫**: 能搜索并提取招标信息
3. **飞书通知**: 任务完成自动发送摘要
4. **端到端**: 3 篇论文完整流程成功

## Sources & References

### Internal References

- 现有调度器: `src/scheduler/scheduler.py`
- 现有收集器: `src/crawlers/collectors.py`
- 现有 Pipeline: `src/pipeline.py`
- Playwright 计划: `docs/plans/2026-03-12-feat-playwright-fallback-url-dedup-plan.md`

### External References

- GLM Coding Plan: https://docs.bigmodel.cn/cn/coding-plan/overview
- 飞书机器人: https://open.feishu.cn/document/client-docs/bot-v3/add-bot
