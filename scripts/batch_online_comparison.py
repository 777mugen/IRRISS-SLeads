#!/usr/bin/env python3
"""
批量对比测试：5 篇文章，对比两种方式与原文
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
from src.logging_config import get_logger
import httpx


async def test_article(doi: str, markdown: str, index: int):
    """测试单篇文章"""
    logger = get_logger()
    
    logger.info(f"\n{'='*60}")
    logger.info(f"文章 {index+1}: {doi}")
    logger.info(f"内容长度: {len(markdown)} 字符")
    logger.info(f"{'='*60}")
    
    # 准备 prompt
    user_prompt = BATCH_EXTRACTION_PROMPT_V1.replace("{markdown_content}", markdown)
    
    # 旧方式
    logger.info("\n[旧方式] 无 response_format")
    from src.llm.client import ZAIClient
    
    old_result = None
    old_success = False
    
    try:
        async with ZAIClient() as client:
            old_response = await client.chat(
                message=user_prompt,
                system_prompt="你是一个专业的学术论文信息提取助手。严格按照规则提取，返回 JSON 格式。",
                temperature=0.1
            )
            
            # 尝试解析
            try:
                cleaned = old_response.strip()
                if cleaned.startswith('```'):
                    lines = cleaned.split('\n')
                    if lines[0].startswith('```'):
                        lines = lines[1:]
                    if lines[-1].startswith('```'):
                        lines = lines[:-1]
                    cleaned = '\n'.join(lines)
                
                old_result = json.loads(cleaned)
                old_success = True
                logger.info(f"  ✅ 成功，字段数: {len(old_result)}")
            except:
                logger.info(f"  ❌ JSON 解析失败，响应长度: {len(old_response)}")
                logger.info(f"  响应前100字符: {old_response[:100]}")
    except Exception as e:
        logger.error(f"  ❌ API 调用失败: {e}")
    
    # 新方式
    logger.info("\n[新方式] 有 response_format")
    
    new_result = None
    new_success = False
    
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
        "response_format": {"type": "json_object"}
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
            
            try:
                new_result = json.loads(new_response)
                new_success = True
                logger.info(f"  ✅ 成功，字段数: {len(new_result)}")
            except:
                logger.info(f"  ❌ JSON 解析失败")
    except Exception as e:
        logger.error(f"  ❌ API 调用失败: {e}")
    
    return {
        "doi": doi,
        "url": f"https://doi.org/{doi}",
        "old_success": old_success,
        "old_result": old_result,
        "new_success": new_success,
        "new_result": new_result
    }


async def main():
    """主函数"""
    logger = get_logger()
    
    # 获取 5 篇文章
    db_url = config.database_url.replace('+asyncpg', '')
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT doi, markdown_content 
                FROM raw_markdown 
                WHERE processing_status = 'completed' 
                LIMIT 5
            """)
        )
        papers = result.fetchall()
    
    logger.info(f"\n{'='*60}")
    logger.info(f"批量对比测试：{len(papers)} 篇文章")
    logger.info(f"{'='*60}")
    
    # 测试每篇文章
    results = []
    for index, (doi, markdown) in enumerate(papers):
        result = await test_article(doi, markdown, index)
        results.append(result)
        
        # 避免请求过快
        if index < len(papers) - 1:
            await asyncio.sleep(2)
    
    # 生成报告
    logger.info(f"\n{'='*60}")
    logger.info("对比报告")
    logger.info(f"{'='*60}")
    
    # 统计
    old_success_count = sum(1 for r in results if r['old_success'])
    new_success_count = sum(1 for r in results if r['new_success'])
    
    logger.info(f"\n成功率:")
    logger.info(f"  旧方式: {old_success_count}/{len(results)} ({old_success_count/len(results)*100:.0f}%)")
    logger.info(f"  新方式: {new_success_count}/{len(results)} ({new_success_count/len(results)*100:.0f}%)")
    
    # 详细对比表
    logger.info(f"\n详细对比:")
    logger.info(f"{'DOI':<40} {'旧方式':<10} {'新方式':<10} {'原文链接'}")
    logger.info(f"{'-'*40} {'-'*10} {'-'*10} {'-'*50}")
    
    for r in results:
        old_status = "✅ 成功" if r['old_success'] else "❌ 失败"
        new_status = "✅ 成功" if r['new_success'] else "❌ 失败"
        logger.info(f"{r['doi']:<40} {old_status:<10} {new_status:<10} {r['url']}")
    
    # 保存详细结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("tmp/batch_comparison")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    report_file = output_dir / f"report_{timestamp}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": timestamp,
            "summary": {
                "total": len(results),
                "old_success": old_success_count,
                "new_success": new_success_count,
                "old_rate": f"{old_success_count/len(results)*100:.0f}%",
                "new_rate": f"{new_success_count/len(results)*100:.0f}%"
            },
            "details": results
        }, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n✅ 详细报告已保存: {report_file}")
    
    # 生成对比表格文件（用于人工校验）
    table_file = output_dir / f"comparison_table_{timestamp}.md"
    with open(table_file, 'w', encoding='utf-8') as f:
        f.write("# 批量对比测试结果\n\n")
        f.write(f"时间: {timestamp}\n\n")
        f.write("## 成功率对比\n\n")
        f.write(f"| 方式 | 成功数 | 成功率 |\n")
        f.write(f"|------|--------|--------|\n")
        f.write(f"| 旧方式（无 response_format） | {old_success_count}/{len(results)} | {old_success_count/len(results)*100:.0f}% |\n")
        f.write(f"| 新方式（有 response_format） | {new_success_count}/{len(results)} | {new_success_count/len(results)*100:.0f}% |\n\n")
        
        f.write("## 详细对比表\n\n")
        f.write(f"| # | DOI | 旧方式 | 新方式 | 原文链接 |\n")
        f.write(f"|---|-----|--------|--------|----------|\n")
        
        for index, r in enumerate(results):
            old_status = "✅" if r['old_success'] else "❌"
            new_status = "✅" if r['new_success'] else "❌"
            f.write(f"| {index+1} | `{r['doi']}` | {old_status} | {new_status} | [原文]({r['url']}) |\n")
        
        # 添加详细字段对比
        f.write("\n## 字段对比详情\n\n")
        
        for index, r in enumerate(results):
            f.write(f"\n### 文章 {index+1}: {r['doi']}\n\n")
            f.write(f"原文链接: {r['url']}\n\n")
            
            if r['old_success'] and r['old_result']:
                f.write("#### 旧方式提取结果\n\n")
                f.write(f"```json\n{json.dumps(r['old_result'], ensure_ascii=False, indent=2)}\n```\n\n")
            
            if r['new_success'] and r['new_result']:
                f.write("#### 新方式提取结果\n\n")
                f.write(f"```json\n{json.dumps(r['new_result'], ensure_ascii=False, indent=2)}\n```\n\n")
    
    logger.info(f"✅ 对比表格已保存: {table_file}")
    
    # 打开所有原文链接
    logger.info(f"\n正在打开浏览器...")
    for r in results:
        import subprocess
        subprocess.run(['open', '-a', 'Google Chrome', r['url']], check=False)
    
    logger.info(f"\n✅ 完成！请查看浏览器进行人工校验")


if __name__ == "__main__":
    asyncio.run(main())
