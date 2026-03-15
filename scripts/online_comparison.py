#!/usr/bin/env python3
"""
在线 API 直接对比（无需等待批处理）
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from src.config import config
from src.prompts.batch_extraction import BATCH_EXTRACTION_PROMPT_V1
from src.llm.client import ZAIClient
from src.logging_config import get_logger


async def test_online_comparison():
    """在线对比测试"""
    logger = get_logger()
    
    # 获取测试文章
    db_url = config.database_url.replace('+asyncpg', '')
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT doi, markdown_content 
                FROM raw_markdown 
                WHERE processing_status = 'completed' 
                LIMIT 1
            """)
        )
        paper = result.fetchone()
    
    if not paper:
        logger.error("没有找到测试文章")
        return
    
    doi, markdown = paper
    logger.info(f"测试文章 DOI: {doi}")
    logger.info(f"内容长度: {len(markdown)} 字符")
    
    # ✅ 不限制内容长度，发送完整内容
    content = markdown
    
    # 准备 prompt
    user_prompt = BATCH_EXTRACTION_PROMPT_V1.replace("{markdown_content}", content)
    
    # 测试 1: 旧方式（无 response_format）
    logger.info("\n" + "=" * 60)
    logger.info("测试 1: 旧方式（无 response_format）")
    logger.info("=" * 60)
    
    async with ZAIClient() as client:
        try:
            old_response = await client.chat(
                message=user_prompt,
                system_prompt="你是一个专业的学术论文信息提取助手。严格按照规则提取，返回 JSON 格式。",
                temperature=0.1
                # ❌ 移除 max_tokens 限制
            )
            
            logger.info(f"响应长度: {len(old_response)} 字符")
            logger.info(f"响应前200字符:\n{old_response[:200]}")
            
            # 尝试解析 JSON
            try:
                # 清理可能的 markdown 代码块
                cleaned = old_response.strip()
                if cleaned.startswith('```'):
                    # 去除代码块标记
                    lines = cleaned.split('\n')
                    if lines[0].startswith('```'):
                        lines = lines[1:]
                    if lines[-1].startswith('```'):
                        lines = lines[:-1]
                    cleaned = '\n'.join(lines)
                
                old_json = json.loads(cleaned)
                logger.info("✅ 旧方式: JSON 解析成功")
                old_success = True
            except json.JSONDecodeError as e:
                logger.error(f"❌ 旧方式: JSON 解析失败 - {e}")
                logger.error(f"原始响应:\n{old_response[:500]}")
                old_json = None
                old_success = False
        except Exception as e:
            logger.error(f"❌ 旧方式 API 调用失败: {e}")
            old_json = None
            old_success = False
    
    # 测试 2: 新方式（有 response_format）
    logger.info("\n" + "=" * 60)
    logger.info("测试 2: 新方式（有 response_format）")
    logger.info("=" * 60)
    
    # 新方式需要直接调用 API（因为 ZAIClient 不支持 response_format）
    import httpx
    
    headers = {
        "Authorization": f"Bearer {config.zai_api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": "glm-4-plus",
        "messages": [
            {"role": "system", "content": "你是一个专业的学术论文信息提取助手。严格按照规则提取，返回 JSON 格式。"},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
        # ❌ 移除 max_tokens 限制
        "response_format": {"type": "json_object"}  # ✅ 关键差异
    }
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as http_client:
            response = await http_client.post(
                "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            new_response = data["choices"][0]["message"]["content"]
            
            logger.info(f"响应长度: {len(new_response)} 字符")
            logger.info(f"响应前200字符:\n{new_response[:200]}")
            
            # 尝试解析 JSON
            try:
                new_json = json.loads(new_response)
                logger.info("✅ 新方式: JSON 解析成功")
                new_success = True
            except json.JSONDecodeError as e:
                logger.error(f"❌ 新方式: JSON 解析失败 - {e}")
                logger.error(f"原始响应:\n{new_response[:500]}")
                new_json = None
                new_success = False
    except Exception as e:
        logger.error(f"❌ 新方式 API 调用失败: {e}")
        new_json = None
        new_success = False
    
    # 对比结果
    logger.info("\n" + "=" * 60)
    logger.info("对比结果")
    logger.info("=" * 60)
    
    logger.info(f"\n旧方式（无 response_format）:")
    logger.info(f"  - JSON 解析: {'✅ 成功' if old_success else '❌ 失败'}")
    if old_json:
        logger.info(f"  - 字段数: {len(old_json)}")
        logger.info(f"  - 字段: {list(old_json.keys())}")
    
    logger.info(f"\n新方式（有 response_format）:")
    logger.info(f"  - JSON 解析: {'✅ 成功' if new_success else '❌ 失败'}")
    if new_json:
        logger.info(f"  - 字段数: {len(new_json)}")
        logger.info(f"  - 字段: {list(new_json.keys())}")
    
    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("tmp/online_comparison")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    result_file = output_dir / f"comparison_{timestamp}.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump({
            "doi": doi,
            "timestamp": timestamp,
            "old_style": {
                "success": old_success,
                "json": old_json,
                "raw": old_response if not old_success else None
            },
            "new_style": {
                "success": new_success,
                "json": new_json,
                "raw": new_response if not new_success else None
            }
        }, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n✅ 结果已保存: {result_file}")
    
    # 结论
    logger.info("\n" + "=" * 60)
    logger.info("结论")
    logger.info("=" * 60)
    
    if old_success and new_success:
        logger.info("✅ 两种方式都成功")
        logger.info(f"   新方式优势: 直接返回合法 JSON，无需清理")
    elif new_success and not old_success:
        logger.info("✅ 新方式明显更好")
        logger.info(f"   旧方式失败，新方式成功")
    elif old_success and not new_success:
        logger.info("⚠️ 意外：旧方式成功，新方式失败")
    else:
        logger.info("❌ 两种方式都失败")
    
    return result_file


if __name__ == "__main__":
    asyncio.run(test_online_comparison())
