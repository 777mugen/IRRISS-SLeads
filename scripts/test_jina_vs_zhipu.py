#!/usr/bin/env python3
"""
Jina vs 智谱网页阅读对比测试

测试目标：
1. 使用 Jina Reader API 尝试获取付费墙论文
2. 对比 Jina 和智谱的成功率
3. 输出对比报告
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Optional
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.crawlers.jina_client import JinaClient
from src.logging_config import get_logger
import httpx


class ZhipuReaderClient:
    """智谱网页阅读客户端"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://open.bigmodel.cn/api/paas/v4"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self._client = httpx.AsyncClient(timeout=60.0)
        self.logger = get_logger()
    
    async def read(self, url: str) -> Optional[str]:
        """读取网页内容"""
        payload = {
            "url": url,
            "return_format": "markdown",
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
            
            if response.status_code == 200:
                data = response.json()
                return data.get('reader_result', {}).get('content', '')
            else:
                return None
        
        except Exception as e:
            self.logger.error(f"智谱读取失败 {url}: {e}")
            return None
    
    async def close(self):
        """关闭客户端"""
        await self._client.aclose()


async def test_comparison(dois: List[str]):
    """对比测试"""
    logger = get_logger()
    
    # 初始化客户端
    from src.config import config
    
    jina_client = JinaClient()
    zhipu_client = ZhipuReaderClient(config.zai_api_key)
    
    results = {
        'jina': {'success': 0, 'failed': 0, 'errors': []},
        'zhipu': {'success': 0, 'failed': 0, 'errors': []}
    }
    
    print("\n" + "=" * 80)
    print("🔍 Jina vs 智谱 对比测试")
    print("=" * 80)
    print(f"测试论文数: {len(dois)} 篇")
    print("=" * 80)
    
    for i, doi in enumerate(dois, 1):
        url = f"https://doi.org/{doi}"
        
        print(f"\n[{i}/{len(dois)}] 测试: {doi}")
        print("-" * 80)
        
        # 测试 Jina
        print(f"  1️⃣  Jina Reader...")
        try:
            start = time.time()
            jina_content = await jina_client.read(url)
            elapsed = time.time() - start
            
            if jina_content and len(jina_content) > 100:
                results['jina']['success'] += 1
                print(f"     ✅ 成功 ({len(jina_content)} 字符, {elapsed:.1f}s)")
            else:
                results['jina']['failed'] += 1
                error = "内容为空或过短"
                results['jina']['errors'].append({'doi': doi, 'error': error})
                print(f"     ❌ 失败: {error}")
        
        except Exception as e:
            results['jina']['failed'] += 1
            results['jina']['errors'].append({'doi': doi, 'error': str(e)})
            print(f"     ❌ 失败: {e}")
        
        # 测试智谱
        print(f"  2️⃣  智谱网页阅读...")
        try:
            start = time.time()
            zhipu_content = await zhipu_client.read(url)
            elapsed = time.time() - start
            
            if zhipu_content and len(zhipu_content) > 100:
                results['zhipu']['success'] += 1
                print(f"     ✅ 成功 ({len(zhipu_content)} 字符, {elapsed:.1f}s)")
            else:
                results['zhipu']['failed'] += 1
                error = "内容为空或过短"
                results['zhipu']['errors'].append({'doi': doi, 'error': error})
                print(f"     ❌ 失败: {error}")
        
        except Exception as e:
            results['zhipu']['failed'] += 1
            results['zhipu']['errors'].append({'doi': doi, 'error': str(e)})
            print(f"     ❌ 失败: {e}")
        
        # 避免请求过快
        await asyncio.sleep(1)
    
    # 关闭客户端
    await jina_client.close()
    await zhipu_client.close()
    
    # 输出对比报告
    print("\n" + "=" * 80)
    print("📊 对比测试结果")
    print("=" * 80)
    
    total = len(dois)
    
    print(f"\n1️⃣  Jina Reader:")
    print(f"   成功: {results['jina']['success']}/{total} ({results['jina']['success']/total*100:.1f}%)")
    print(f"   失败: {results['jina']['failed']}/{total} ({results['jina']['failed']/total*100:.1f}%)")
    
    print(f"\n2️⃣  智谱网页阅读:")
    print(f"   成功: {results['zhipu']['success']}/{total} ({results['zhipu']['success']/total*100:.1f}%)")
    print(f"   失败: {results['zhipu']['failed']}/{total} ({results['zhipu']['failed']/total*100:.1f}%)")
    
    print(f"\n3️⃣  对比分析:")
    jina_rate = results['jina']['success'] / total * 100
    zhipu_rate = results['zhipu']['success'] / total * 100
    
    if jina_rate > zhipu_rate:
        print(f"   ✅ Jina 更优 ({jina_rate:.1f}% vs {zhipu_rate:.1f}%)")
        print(f"   📈 Jina 成功率高出 {jina_rate - zhipu_rate:.1f}%")
    elif zhipu_rate > jina_rate:
        print(f"   ✅ 智谱更优 ({zhipu_rate:.1f}% vs {jina_rate:.1f}%)")
        print(f"   📈 智谱成功率高出 {zhipu_rate - jina_rate:.1f}%")
    else:
        print(f"   ➖ 两者相同 ({jina_rate:.1f}%)")
    
    # 输出错误分析
    if results['jina']['errors']:
        print(f"\n4️⃣  Jina 错误分析:")
        error_types = {}
        for error in results['jina']['errors']:
            error_msg = error['error']
            # 提取错误类型
            if '403' in str(error_msg):
                error_type = '403 Forbidden (付费墙)'
            elif '429' in str(error_msg):
                error_type = '429 Rate Limit'
            elif '500' in str(error_msg):
                error_type = '500 Server Error'
            else:
                error_type = 'Other'
            
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        for error_type, count in error_types.items():
            print(f"   {error_type}: {count} 次")
    
    if results['zhipu']['errors']:
        print(f"\n5️⃣  智谱错误分析:")
        error_types = {}
        for error in results['zhipu']['errors']:
            error_msg = error['error']
            # 提取错误类型
            if '400' in str(error_msg):
                error_type = '400 Bad Request (付费墙)'
            elif '429' in str(error_msg):
                error_type = '429 Rate Limit'
            elif '500' in str(error_msg):
                error_type = '500 Server Error'
            else:
                error_type = 'Other'
            
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        for error_type, count in error_types.items():
            print(f"   {error_type}: {count} 次")
    
    print("\n" + "=" * 80)
    print("✅ 测试完成")
    print("=" * 80)
    
    # 返回结果
    return results


async def main():
    """主函数"""
    # 测试之前失败的 DOI（Taylor & Francis 付费墙）
    test_dois = [
        "10.1080/17482631.2026.2640184",
        "10.1080/19490976.2026.2638002",
        "10.1080/17482631.2026.2637803",
        "10.1080/08916934.2026.2631208",
        "10.1080/2162402X.2026.2633012",
        "10.1080/10253890.2026.2635367",
        "10.1080/22423982.2026.2634479",
        "10.1080/19490976.2026.2630563",
        "10.1080/17482631.2026.2631081",
        "10.1080/10872981.2026.2627020",
    ]
    
    await test_comparison(test_dois)


if __name__ == "__main__":
    asyncio.run(main())
