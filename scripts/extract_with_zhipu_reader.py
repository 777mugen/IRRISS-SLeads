#!/usr/bin/env python3
"""
智谱网页阅读 + 结构化输出 两步提取流程

独立脚本，不依赖 Jina，作为新的分支流程
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from src.db.models import RawMarkdown, PaperLead
from src.db.utils import get_session
from src.config import config
from src.logging_config import get_logger
import httpx


class ZhipuReaderClient:
    """智谱网页阅读客户端"""
    
    def __init__(self):
        self.api_key = config.zai_api_key
        self.base_url = "https://open.bigmodel.cn/api/paas/v4"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self._client = httpx.AsyncClient(timeout=60.0)
        self.logger = get_logger()
    
    async def read(self, url: str, return_format: str = "markdown") -> Optional[dict]:
        """读取网页内容"""
        payload = {
            "url": url,
            "return_format": return_format,
            "retain_images": False,
            "with_links_summary": False,
            "timeout": 30
        }
        
        try:
            response = await self._client.post(
                f"{self.base_url}/reader",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 429:
                # 速率限制，等待后重试
                retry_after = int(response.headers.get('Retry-After', 60))
                self.logger.warning(f"Rate limited, waiting {retry_after}s")
                await asyncio.sleep(retry_after)
                return await self.read(url, return_format)
            
            response.raise_for_status()
            return response.json()
        
        except Exception as e:
            self.logger.error(f"Failed to read {url}: {e}")
            return None
    
    async def close(self):
        """关闭客户端"""
        await self._client.aclose()


class ZhipuExtractor:
    """智谱结构化输出提取器"""
    
    def __init__(self):
        self.api_key = config.zai_api_key
        self.base_url = "https://open.bigmodel.cn/api/paas/v4"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self._client = httpx.AsyncClient(timeout=120.0)
        self.logger = get_logger()
    
    async def extract(self, content: str, prompt: str) -> Optional[dict]:
        """提取结构化信息"""
        payload = {
            "model": "glm-4-plus",
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的学术论文信息提取助手。严格按照规则提取，返回 JSON 格式。"
                },
                {
                    "role": "user",
                    "content": f"{prompt}\n\n---\n\n{content}"
                }
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}  # ✅ 官方结构化输出
        }
        
        try:
            response = await self._client.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload
            )
            
            response.raise_for_status()
            data = response.json()
            
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
        
        except Exception as e:
            self.logger.error(f"Failed to extract: {e}")
            return None
    
    async def close(self):
        """关闭客户端"""
        await self._client.aclose()


async def extract_papers_with_zhipu_reader(
    limit: int = 1000,
    concurrency: int = 5,
    batch_size: int = 50
):
    """
    使用智谱网页阅读 + 结构化输出提取论文
    
    Args:
        limit: 最大处理论文数
        concurrency: 并发数（网页阅读）
        batch_size: 批处理大小（结构化输出）
    """
    logger = get_logger()
    
    logger.info(f"\n{'='*60}")
    logger.info(f"智谱网页阅读 + 结构化输出提取流程")
    logger.info(f"{'='*60}")
    logger.info(f"配置:")
    logger.info(f"  - 最大处理数: {limit}")
    logger.info(f"  - 并发数: {concurrency}")
    logger.info(f"  - 批处理大小: {batch_size}")
    
    # 步骤 1: 从数据库获取待处理 DOI
    logger.info(f"\n步骤 1: 获取待处理 DOI")
    
    async with get_session() as session:
        query = (
            select(RawMarkdown.doi)
            .where(RawMarkdown.processing_status == 'pending')
            .limit(limit)
        )
        result = await session.execute(query)
        dois = [row[0] for row in result.fetchall()]
    
    logger.info(f"  找到 {len(dois)} 篇待处理论文")
    
    if not dois:
        logger.info("没有待处理论文")
        return
    
    # 步骤 2: 网页阅读（并发）
    logger.info(f"\n步骤 2: 网页阅读（并发数: {concurrency}）")
    
    reader = ZhipuReaderClient()
    semaphore = asyncio.Semaphore(concurrency)
    
    contents = {}
    
    async def read_doi(doi: str, index: int):
        """读取单个 DOI"""
        async with semaphore:
            try:
                logger.info(f"  [{index+1}/{len(dois)}] 读取: {doi}")
                
                result = await reader.read(f"https://doi.org/{doi}")
                
                if result and 'reader_result' in result:
                    content = result['reader_result']['content']
                    contents[doi] = content
                    logger.info(f"  [{index+1}/{len(dois)}] ✅ 成功，长度: {len(content)}")
                    return True
                else:
                    logger.error(f"  [{index+1}/{len(dois)}] ❌ 失败：无内容")
                    return False
            except Exception as e:
                logger.error(f"  [{index+1}/{len(dois)}] ❌ 失败: {e}")
                return False
    
    # 并发读取
    tasks = [read_doi(doi, i) for i, doi in enumerate(dois)]
    results = await asyncio.gather(*tasks)
    
    success_count = sum(results)
    logger.info(f"\n网页阅读完成: {success_count}/{len(dois)} 成功")
    
    await reader.close()
    
    # 步骤 3: 保存到数据库
    logger.info(f"\n步骤 3: 保存内容到数据库")
    
    async with get_session() as session:
        for doi, content in contents.items():
            # 更新 raw_markdown 表
            stmt = (
                update(RawMarkdown)
                .where(RawMarkdown.doi == doi)
                .values(
                    markdown_content=content,
                    processing_status='content_ready',
                    pipeline_source='pipeline_v2_zhipu_reader'  # ✅ 标记来源
                )
            )
            await session.execute(stmt)
        
        await session.commit()
    
    logger.info(f"  已保存 {len(contents)} 篇内容")
    
    # 步骤 4: 结构化输出（批量）
    logger.info(f"\n步骤 4: 结构化输出（批处理大小: {batch_size}）")
    
    # 加载 Prompt
    from src.prompts.batch_extraction import BATCH_EXTRACTION_PROMPT_V1
    
    extractor = ZhipuExtractor()
    
    extracted = {}
    errors = []
    
    for i, (doi, content) in enumerate(contents.items()):
        try:
            logger.info(f"  [{i+1}/{len(contents)}] 提取: {doi}")
            
            result = await extractor.extract(content, BATCH_EXTRACTION_PROMPT_V1)
            
            if result:
                extracted[doi] = result
                logger.info(f"  [{i+1}/{len(contents)}] ✅ 成功")
            else:
                errors.append(doi)
                logger.error(f"  [{i+1}/{len(contents)}] ❌ 失败")
        
        except Exception as e:
            errors.append(doi)
            logger.error(f"  [{i+1}/{len(contents)}] ❌ 失败: {e}")
        
        # 每处理 batch_size 篇保存一次
        if (i + 1) % batch_size == 0:
            logger.info(f"  保存进度...")
            # TODO: 保存到 paper_leads 表
    
    await extractor.close()
    
    # 步骤 5: 保存提取结果
    logger.info(f"\n步骤 5: 保存提取结果")
    
    # TODO: 实现 paper_leads 保存逻辑
    
    # 生成报告
    logger.info(f"\n{'='*60}")
    logger.info(f"提取完成")
    logger.info(f"{'='*60}")
    logger.info(f"总论文数: {len(dois)}")
    logger.info(f"网页阅读成功: {success_count}/{len(dois)} ({success_count/len(dois)*100:.0f}%)")
    logger.info(f"结构化提取成功: {len(extracted)}/{len(contents)} ({len(extracted)/len(contents)*100:.0f}%)")
    logger.info(f"总成功率: {len(extracted)/len(dois)*100:.0f}%")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='使用智谱网页阅读提取论文')
    parser.add_argument('--limit', type=int, default=1000, help='最大处理论文数')
    parser.add_argument('--concurrency', type=int, default=5, help='并发数')
    parser.add_argument('--batch-size', type=int, default=50, help='批处理大小')
    
    args = parser.parse_args()
    
    asyncio.run(extract_papers_with_zhipu_reader(
        limit=args.limit,
        concurrency=args.concurrency,
        batch_size=args.batch_size
    ))


if __name__ == "__main__":
    main()
