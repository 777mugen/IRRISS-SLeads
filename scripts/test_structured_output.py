"""
测试结构化输出 vs 当前方式的准确性对比

步骤：
1. 从数据库提取 10 篇文章
2. 创建两个批处理文件（旧方式 vs 新方式）
3. 上传并执行
4. 对比结果
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import json
from datetime import datetime

from sqlalchemy import select

from src.db.models import RawMarkdown
from src.db.utils import get_session
from src.llm.batch_client import ZhiPuBatchClient
from src.processors.batch_processor import BatchProcessor
from src.prompts.batch_extraction import BATCH_EXTRACTION_PROMPT_V1
from src.logging_config import get_logger


async def get_test_papers(limit: int = 10) -> list[RawMarkdown]:
    """从数据库获取测试文章"""
    async with get_session() as session:
        query = (
            select(RawMarkdown)
            .where(RawMarkdown.processing_status == 'pending')
            .limit(limit)
        )
        result = await session.execute(query)
        papers = result.scalars().all()
        return list(papers)


def build_old_style_batch(papers: list[RawMarkdown], output_path: Path):
    """构建旧方式批处理文件（无 response_format）"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for paper in papers:
            user_content = BATCH_EXTRACTION_PROMPT_V1.replace(
                "{markdown_content}",
                paper.markdown_content
            )
            
            request = {
                "custom_id": f"old_doi_{paper.doi.replace('/', '_')}",
                "method": "POST",
                "url": "/v4/chat/completions",
                "body": {
                    "model": "glm-4-plus",
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一个专业的学术论文信息提取助手。严格按照规则提取，返回 JSON 格式。"
                        },
                        {
                            "role": "user",
                            "content": user_content
                        }
                    ],
                    "temperature": 0.1,
                    "max_tokens": 4096
                    # ❌ 没有 response_format
                }
            }
            
            f.write(json.dumps(request, ensure_ascii=False) + '\n')
    
    return output_path


def build_new_style_batch(papers: list[RawMarkdown], output_path: Path):
    """构建新方式批处理文件（有 response_format）"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for paper in papers:
            user_content = BATCH_EXTRACTION_PROMPT_V1.replace(
                "{markdown_content}",
                paper.markdown_content
            )
            
            request = {
                "custom_id": f"new_doi_{paper.doi.replace('/', '_')}",
                "method": "POST",
                "url": "/v4/chat/completions",
                "body": {
                    "model": "glm-4-plus",
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一个专业的学术论文信息提取助手。严格按照规则提取，返回 JSON 格式。"
                        },
                        {
                            "role": "user",
                            "content": user_content
                        }
                    ],
                    "temperature": 0.1,
                    "max_tokens": 4096,
                    "response_format": {"type": "json_object"}  # ✅ 官方结构化输出
                }
            }
            
            f.write(json.dumps(request, ensure_ascii=False) + '\n')
    
    return output_path


async def run_comparison():
    """运行对比测试"""
    logger = get_logger()
    
    # Step 1: 获取测试文章
    logger.info("=" * 60)
    logger.info("Step 1: 从数据库获取 10 篇测试文章")
    logger.info("=" * 60)
    
    papers = await get_test_papers(limit=10)
    
    if not papers:
        logger.error("没有找到待处理的文章！")
        return
    
    logger.info(f"✅ 获取到 {len(papers)} 篇文章")
    
    # Step 2: 创建输出目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"tmp/comparison_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Step 3: 构建批处理文件
    logger.info("\n" + "=" * 60)
    logger.info("Step 2: 构建批处理文件")
    logger.info("=" * 60)
    
    old_batch_file = output_dir / "old_style.jsonl"
    new_batch_file = output_dir / "new_style.jsonl"
    
    build_old_style_batch(papers, old_batch_file)
    logger.info(f"✅ 旧方式批处理文件: {old_batch_file}")
    
    build_new_style_batch(papers, new_batch_file)
    logger.info(f"✅ 新方式批处理文件: {new_batch_file}")
    
    # Step 4: 上传并执行批处理
    logger.info("\n" + "=" * 60)
    logger.info("Step 3: 上传并执行批处理任务")
    logger.info("=" * 60)
    
    async with ZhiPuBatchClient() as client:
        # 旧方式
        logger.info("\n--- 旧方式（无 response_format）---")
        old_file_id = await client.upload_file(old_batch_file)
        old_batch_id = await client.create_batch(old_file_id)
        logger.info(f"✅ 旧方式批处理任务已创建: {old_batch_id}")
        
        # 新方式
        logger.info("\n--- 新方式（有 response_format）---")
        new_file_id = await client.upload_file(new_batch_file)
        new_batch_id = await client.create_batch(new_file_id)
        logger.info(f"✅ 新方式批处理任务已创建: {new_batch_id}")
        
        # Step 5: 等待完成
        logger.info("\n" + "=" * 60)
        logger.info("Step 4: 等待批处理完成")
        logger.info("=" * 60)
        
        logger.info("\n--- 等待旧方式完成 ---")
        old_batch = await client.wait_for_completion(
            old_batch_id,
            poll_interval=30,
            max_wait=3600
        )
        
        logger.info("\n--- 等待新方式完成 ---")
        new_batch = await client.wait_for_completion(
            new_batch_id,
            poll_interval=30,
            max_wait=3600
        )
        
        # Step 6: 下载结果
        logger.info("\n" + "=" * 60)
        logger.info("Step 5: 下载结果")
        logger.info("=" * 60)
        
        old_result_file = output_dir / "old_results.jsonl"
        new_result_file = output_dir / "new_results.jsonl"
        
        await client.download_result(
            old_batch.get('output_file_id'),
            old_result_file
        )
        logger.info(f"✅ 旧方式结果: {old_result_file}")
        
        await client.download_result(
            new_batch.get('output_file_id'),
            new_result_file
        )
        logger.info(f"✅ 新方式结果: {new_result_file}")
        
        # Step 7: 分析结果
        logger.info("\n" + "=" * 60)
        logger.info("Step 6: 分析结果")
        logger.info("=" * 60)
        
        analyze_results(old_result_file, new_result_file, papers, output_dir)


def analyze_results(
    old_file: Path,
    new_file: Path,
    papers: list[RawMarkdown],
    output_dir: Path
):
    """分析对比结果"""
    logger = get_logger()
    
    # 解析结果
    old_results = {}
    new_results = {}
    
    with open(old_file, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            custom_id = data.get('custom_id')
            if data.get('error'):
                old_results[custom_id] = {"error": data.get('error')}
            else:
                try:
                    content = data['response']['body']['choices'][0]['message']['content']
                    old_results[custom_id] = json.loads(content)
                except:
                    old_results[custom_id] = {"parse_error": True}
    
    with open(new_file, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            custom_id = data.get('custom_id')
            if data.get('error'):
                new_results[custom_id] = {"error": data.get('error')}
            else:
                try:
                    content = data['response']['body']['choices'][0]['message']['content']
                    new_results[custom_id] = json.loads(content)
                except:
                    new_results[custom_id] = {"parse_error": True}
    
    # 统计
    old_success = sum(1 for r in old_results.values() if 'error' not in r and 'parse_error' not in r)
    new_success = sum(1 for r in new_results.values() if 'error' not in r and 'parse_error' not in r)
    
    old_parse_errors = sum(1 for r in old_results.values() if 'parse_error' in r)
    new_parse_errors = sum(1 for r in new_results.values() if 'parse_error' in r)
    
    # 保存对比报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_papers": len(papers),
        "old_style": {
            "success": old_success,
            "parse_errors": old_parse_errors,
            "errors": len(old_results) - old_success - old_parse_errors,
            "success_rate": f"{old_success / len(papers) * 100:.1f}%"
        },
        "new_style": {
            "success": new_success,
            "parse_errors": new_parse_errors,
            "errors": len(new_results) - new_success - new_parse_errors,
            "success_rate": f"{new_success / len(papers) * 100:.1f}%"
        },
        "improvement": {
            "success_rate": f"{(new_success - old_success) / len(papers) * 100:+.1f}%",
            "parse_errors": f"{old_parse_errors - new_parse_errors:+d}"
        }
    }
    
    report_file = output_dir / "comparison_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    logger.info("\n" + "=" * 60)
    logger.info("对比结果")
    logger.info("=" * 60)
    logger.info(f"总文章数: {len(papers)}")
    logger.info(f"\n旧方式（无 response_format）:")
    logger.info(f"  - 成功: {old_success} ({report['old_style']['success_rate']})")
    logger.info(f"  - 解析错误: {old_parse_errors}")
    logger.info(f"  - API 错误: {report['old_style']['errors']}")
    logger.info(f"\n新方式（有 response_format）:")
    logger.info(f"  - 成功: {new_success} ({report['new_style']['success_rate']})")
    logger.info(f"  - 解析错误: {new_parse_errors}")
    logger.info(f"  - API 错误: {report['new_style']['errors']}")
    logger.info(f"\n改进:")
    logger.info(f"  - 成功率提升: {report['improvement']['success_rate']}")
    logger.info(f"  - 解析错误减少: {report['improvement']['parse_errors']}")
    logger.info(f"\n✅ 报告已保存: {report_file}")
    
    # 保存详细结果用于浏览器校验
    save_detailed_results(old_results, new_results, papers, output_dir)


def save_detailed_results(
    old_results: dict,
    new_results: dict,
    papers: list[RawMarkdown],
    output_dir: Path
):
    """保存详细结果用于浏览器校验"""
    logger = get_logger()
    
    comparison_data = []
    
    for paper in papers:
        doi_key = paper.doi.replace('/', '_')
        old_key = f"old_doi_{doi_key}"
        new_key = f"new_doi_{doi_key}"
        
        comparison_data.append({
            "doi": paper.doi,
            "pmid": paper.pmid,
            "old_result": old_results.get(old_key, {}),
            "new_result": new_results.get(new_key, {}),
            "source_url": f"https://doi.org/{paper.doi}"
        })
    
    detail_file = output_dir / "detailed_comparison.json"
    with open(detail_file, 'w', encoding='utf-8') as f:
        json.dump(comparison_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✅ 详细对比数据已保存: {detail_file}")
    logger.info(f"\n可以通过以下方式校验:")
    logger.info(f"  1. 打开 Web Dashboard: http://localhost:8000")
    logger.info(f"  2. 查看详细对比文件: {detail_file}")
    logger.info(f"  3. 访问原文链接验证准确性")


if __name__ == "__main__":
    asyncio.run(run_comparison())
