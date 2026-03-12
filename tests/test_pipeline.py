#!/usr/bin/env python3
"""
Test script for lead discovery pipeline.
测试脚本。
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import config
from src.logging_config import setup_logging, get_logger


async def test_jina_search():
    """测试 Jina 搜索"""
    from src.crawlers.jina_client import JinaClient
    
    async with JinaClient() as client:
        # 测试读取一个 PubMed 页面
        test_url = "https://pubmed.ncbi.nlm.nih.gov/38049430/"
        print(f"测试读取: {test_url}")
        
        content = await client.read(test_url)
        print(f"内容长度: {len(content)} 字符")
        print(f"前 500 字符:\n{content[:500]}...")
        
        return content


async def test_llm_extraction(content: str):
    """测试 LLM 提取"""
    from src.extractors.paper_extractor import PaperExtractor
    
    async with PaperExtractor() as extractor:
        print("\n测试 LLM 提取...")
        result = await extractor.extract(content)
        
        print(f"提取结果: {result}")
        return result


async def test_scoring(extracted: dict):
    """测试评分"""
    from src.scoring.paper_scorer import PaperScorer
    
    scorer = PaperScorer()
    
    # 添加评分所需的字段
    test_lead = {
        **extracted,
        'feedback_status': '未处理',
    }
    
    # 处理日期
    if 'published_at' in test_lead and isinstance(test_lead['published_at'], str):
        from datetime import datetime
        try:
            test_lead['published_at'] = datetime.strptime(test_lead['published_at'], '%Y-%m-%d').date()
        except:
            test_lead['published_at'] = None
    
    score, grade = scorer.score_lead(test_lead)
    print(f"\n评分结果: {score} 分, 等级 {grade}")
    
    return score, grade


async def main():
    """主测试函数"""
    setup_logging(log_level="INFO")
    logger = get_logger()
    
    print("=" * 60)
    print("销售线索发现系统 - 组件测试")
    print("=" * 60)
    
    try:
        # 1. 测试 Jina 读取
        print("\n[1/3] 测试 Jina Reader API...")
        content = await test_jina_search()
        
        # 2. 测试 LLM 提取
        print("\n[2/3] 测试 GLM-5 提取...")
        extracted = await test_llm_extraction(content)
        
        # 3. 测试评分
        print("\n[3/3] 测试评分引擎...")
        await test_scoring(extracted)
        
        print("\n" + "=" * 60)
        print("所有测试通过!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
