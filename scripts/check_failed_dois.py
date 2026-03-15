#!/usr/bin/env python3
"""
检查失败 DOI 的详细原因
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from src.config import config
from src.logging_config import get_logger


async def check_doi(doi: str):
    """检查单个 DOI"""
    logger = get_logger()
    
    api_key = config.zai_api_key
    base_url = "https://open.bigmodel.cn/api/paas/v4"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    url = f"https://doi.org/{doi}"
    
    logger.info(f"\n{'='*60}")
    logger.info(f"检查 DOI: {doi}")
    logger.info(f"URL: {url}")
    logger.info(f"{'='*60}")
    
    # 测试 1: 检查 URL 是否可访问
    logger.info(f"\n步骤 1: 检查 DOI 链接是否可访问")
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            logger.info(f"  ✅ DOI 链接可访问")
            logger.info(f"  状态码: {response.status_code}")
            logger.info(f"  最终 URL: {response.url}")
            logger.info(f"  内容长度: {len(response.content)} 字节")
    except Exception as e:
        logger.error(f"  ❌ DOI 链接不可访问: {e}")
    
    # 测试 2: 调用智谱网页阅读 API（详细错误）
    logger.info(f"\n步骤 2: 调用智谱网页阅读 API")
    
    payload = {
        "url": url,
        "return_format": "markdown",
        "retain_images": False,
        "with_links_summary": False,
        "timeout": 30
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{base_url}/reader",
                headers=headers,
                json=payload
            )
            
            logger.info(f"  状态码: {response.status_code}")
            logger.info(f"  响应头: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"  ✅ 成功")
                logger.info(f"  内容长度: {len(data.get('reader_result', {}).get('content', ''))}")
            else:
                logger.error(f"  ❌ 失败")
                logger.error(f"  响应内容: {response.text}")
                
                # 尝试解析错误信息
                try:
                    error_data = response.json()
                    logger.error(f"  错误详情: {error_data}")
                except:
                    pass
    
    except Exception as e:
        logger.error(f"  ❌ 请求失败: {e}")
    
    # 测试 3: 尝试不同的参数
    logger.info(f"\n步骤 3: 尝试不同参数")
    
    # 尝试 text 格式
    payload_text = {
        "url": url,
        "return_format": "text",  # 改为 text
        "retain_images": False,
        "with_links_summary": False,
        "timeout": 30
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{base_url}/reader",
                headers=headers,
                json=payload_text
            )
            
            logger.info(f"  text 格式状态码: {response.status_code}")
            
            if response.status_code == 200:
                logger.info(f"  ✅ text 格式成功")
            else:
                logger.error(f"  ❌ text 格式失败: {response.text[:200]}")
    
    except Exception as e:
        logger.error(f"  ❌ text 格式请求失败: {e}")


async def main():
    """主函数"""
    # 检查失败的两篇
    failed_dois = [
        "10.3748/wjg.v32.i9.115259",
        "10.1021/acs.jmedchem.5c03498"
    ]
    
    for doi in failed_dois:
        await check_doi(doi)
        await asyncio.sleep(2)  # 避免请求过快


if __name__ == "__main__":
    asyncio.run(main())
