#!/usr/bin/env python3
"""
智谱网页阅读 API 测试：并发限制验证

测试不同并发数下的表现，确定最佳配置
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from src.config import config
from src.logging_config import get_logger


class ZhipuReaderClient:
    """智谱网页阅读 API 客户端"""
    
    def __init__(self):
        self.api_key = config.zai_api_key
        self.base_url = "https://open.bigmodel.cn/api/paas/v4"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self._client = httpx.AsyncClient(timeout=60.0)
        self.logger = get_logger()
    
    async def read(self, url: str, return_format: str = "markdown") -> dict:
        """
        读取网页内容
        
        Args:
            url: 网页 URL
            return_format: 返回格式（markdown 或 text）
            
        Returns:
            网页内容字典
        """
        payload = {
            "url": url,
            "return_format": return_format,
            "retain_images": False,
            "with_links_summary": False,
            "timeout": 30
        }
        
        response = await self._client.post(
            f"{self.base_url}/reader",
            headers=self.headers,
            json=payload
        )
        
        if response.status_code == 429:
            # 速率限制
            retry_after = response.headers.get('Retry-After', 60)
            raise Exception(f"Rate limited, retry after {retry_after}s")
        
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """关闭客户端"""
        await self._client.aclose()


async def test_concurrency(test_dois: list[str], concurrency: int):
    """测试指定并发数"""
    logger = get_logger()
    
    logger.info(f"\n{'='*60}")
    logger.info(f"测试并发数: {concurrency}")
    logger.info(f"测试文章数: {len(test_dois)}")
    logger.info(f"{'='*60}")
    
    client = ZhipuReaderClient()
    semaphore = asyncio.Semaphore(concurrency)
    
    results = []
    start_time = time.time()
    
    async def process_doi(doi: str, index: int):
        """处理单个 DOI"""
        async with semaphore:
            try:
                url = f"https://doi.org/{doi}"
                logger.info(f"[{index+1}/{len(test_dois)}] 开始读取: {doi}")
                
                result = await client.read(url)
                content_length = len(result.get('reader_result', {}).get('content', ''))
                
                logger.info(f"[{index+1}/{len(test_dois)}] ✅ 成功，内容长度: {content_length}")
                
                return {
                    "doi": doi,
                    "success": True,
                    "content_length": content_length,
                    "error": None
                }
            except Exception as e:
                logger.error(f"[{index+1}/{len(test_dois)}] ❌ 失败: {e}")
                return {
                    "doi": doi,
                    "success": False,
                    "content_length": 0,
                    "error": str(e)
                }
    
    try:
        # 并发处理
        tasks = [process_doi(doi, i) for i, doi in enumerate(test_dois)]
        results = await asyncio.gather(*tasks)
        
        elapsed = time.time() - start_time
        
        # 统计
        success = sum(1 for r in results if r['success'])
        failed = len(results) - success
        rate_429 = sum(1 for r in results if '429' in r.get('error', ''))
        
        logger.info(f"\n测试结果:")
        logger.info(f"  成功: {success}/{len(results)}")
        logger.info(f"  失败: {failed}")
        logger.info(f"  429 错误: {rate_429}")
        logger.info(f"  耗时: {elapsed:.1f} 秒")
        logger.info(f"  速度: {len(results)/elapsed*60:.1f} 篇/分钟")
        
        return {
            "concurrency": concurrency,
            "total": len(results),
            "success": success,
            "failed": failed,
            "rate_429": rate_429,
            "elapsed": elapsed,
            "speed": len(results)/elapsed*60
        }
    
    finally:
        await client.close()


async def main():
    """主函数"""
    logger = get_logger()
    
    # 测试 DOI 列表（5 篇文章）
    test_dois = [
        "10.21037/tcr-2025-aw-2287",
        "10.3748/wjg.v32.i9.115259",
        "10.1021/acs.jmedchem.5c03498",
        "10.1021/jacsau.5c01509",
        "10.21037/jgo-2025-750"
    ]
    
    logger.info(f"\n{'='*60}")
    logger.info(f"智谱网页阅读 API 并发测试")
    logger.info(f"{'='*60}")
    logger.info(f"测试文章: {len(test_dois)} 篇")
    logger.info(f"测试并发: 3, 5, 10")
    
    results = []
    
    # 测试不同并发数
    for concurrency in [3, 5, 10]:
        result = await test_concurrency(test_dois, concurrency)
        results.append(result)
        
        # 等待 10 秒再进行下一轮测试
        if concurrency < 10:
            logger.info(f"\n等待 10 秒后进行下一轮测试...")
            await asyncio.sleep(10)
    
    # 生成报告
    logger.info(f"\n{'='*60}")
    logger.info(f"测试报告")
    logger.info(f"{'='*60}")
    
    logger.info(f"\n| 并发数 | 成功率 | 429错误 | 耗时 | 速度(篇/分钟) |")
    logger.info(f"|--------|--------|---------|------|--------------|")
    
    for r in results:
        success_rate = r['success'] / r['total'] * 100
        logger.info(f"| {r['concurrency']} | {success_rate:.0f}% | {r['rate_429']} | {r['elapsed']:.1f}s | {r['speed']:.1f} |")
    
    # 推荐
    best = max(results, key=lambda x: x['success'] / x['total'] * x['speed'])
    
    logger.info(f"\n推荐配置:")
    logger.info(f"  并发数: {best['concurrency']}")
    logger.info(f"  预计速度: {best['speed']:.1f} 篇/分钟")
    
    # 保存报告
    output_dir = Path("tmp/reader_test")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    report_file = output_dir / f"concurrency_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n✅ 测试报告已保存: {report_file}")


if __name__ == "__main__":
    asyncio.run(main())
