#!/usr/bin/env python3
"""
持续监控批处理任务状态
完成后自动下载结果并生成对比报告
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm.batch_client import ZhiPuBatchClient
from src.logging_config import get_logger


async def monitor_batch(batch_id: str, label: str):
    """监控单个批处理任务"""
    logger = get_logger()
    
    async with ZhiPuBatchClient() as client:
        logger.info(f"开始监控 {label}: {batch_id}")
        
        # 轮询直到完成
        batch = await client.wait_for_completion(
            batch_id,
            poll_interval=120,  # 每2分钟检查一次
            max_wait=7200  # 最长等待2小时
        )
        
        # 下载结果
        output_file_id = batch.get('output_file_id')
        if output_file_id:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path(f"tmp/comparison_test/results_{label}_{timestamp}.jsonl")
            await client.download_result(output_file_id, output_path)
            logger.info(f"✅ {label} 完成！结果已保存: {output_path}")
            return output_path
        else:
            logger.error(f"❌ {label} 完成但没有输出文件")
            return None


async def analyze_results(old_file: Path, new_file: Path):
    """分析对比结果"""
    logger = get_logger()
    
    logger.info("\n" + "=" * 60)
    logger.info("开始分析对比结果")
    logger.info("=" * 60)
    
    # 解析结果
    old_results = {}
    new_results = {}
    
    # 解析旧方式结果
    with open(old_file, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            custom_id = data.get('custom_id', '')
            
            if data.get('error'):
                old_results[custom_id] = {"error": data.get('error')}
            else:
                try:
                    content = data['response']['body']['choices'][0]['message']['content']
                    # 尝试解析 JSON
                    try:
                        old_results[custom_id] = {
                            "raw": content,
                            "parsed": json.loads(content),
                            "parse_success": True
                        }
                    except json.JSONDecodeError as e:
                        old_results[custom_id] = {
                            "raw": content,
                            "parse_error": str(e),
                            "parse_success": False
                        }
                except Exception as e:
                    old_results[custom_id] = {"error": str(e)}
    
    # 解析新方式结果
    with open(new_file, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            custom_id = data.get('custom_id', '')
            
            if data.get('error'):
                new_results[custom_id] = {"error": data.get('error')}
            else:
                try:
                    content = data['response']['body']['choices'][0]['message']['content']
                    # 尝试解析 JSON
                    try:
                        new_results[custom_id] = {
                            "raw": content,
                            "parsed": json.loads(content),
                            "parse_success": True
                        }
                    except json.JSONDecodeError as e:
                        new_results[custom_id] = {
                            "raw": content,
                            "parse_error": str(e),
                            "parse_success": False
                        }
                except Exception as e:
                    new_results[custom_id] = {"error": str(e)}
    
    # 统计
    total = len(old_results)
    old_success = sum(1 for r in old_results.values() if r.get('parse_success'))
    new_success = sum(1 for r in new_results.values() if r.get('parse_success'))
    
    old_parse_errors = sum(1 for r in old_results.values() if not r.get('parse_success') and 'parse_error' in r)
    new_parse_errors = sum(1 for r in new_results.values() if not r.get('parse_success') and 'parse_error' in r)
    
    # 生成报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_papers": total,
        "old_style": {
            "success": old_success,
            "parse_errors": old_parse_errors,
            "api_errors": total - old_success - old_parse_errors,
            "success_rate": f"{old_success / total * 100:.1f}%"
        },
        "new_style": {
            "success": new_success,
            "parse_errors": new_parse_errors,
            "api_errors": total - new_success - new_parse_errors,
            "success_rate": f"{new_success / total * 100:.1f}%"
        },
        "improvement": {
            "success_rate": f"{(new_success - old_success) / total * 100:+.1f}%",
            "parse_errors_reduced": old_parse_errors - new_parse_errors
        }
    }
    
    # 保存报告
    report_file = Path("tmp/comparison_test/comparison_report.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # 打印报告
    logger.info("\n" + "=" * 60)
    logger.info("对比结果")
    logger.info("=" * 60)
    logger.info(f"总文章数: {total}")
    logger.info(f"\n旧方式（无 response_format）:")
    logger.info(f"  - JSON 解析成功: {old_success} ({report['old_style']['success_rate']})")
    logger.info(f"  - JSON 解析失败: {old_parse_errors}")
    logger.info(f"  - API 错误: {report['old_style']['api_errors']}")
    logger.info(f"\n新方式（有 response_format）:")
    logger.info(f"  - JSON 解析成功: {new_success} ({report['new_style']['success_rate']})")
    logger.info(f"  - JSON 解析失败: {new_parse_errors}")
    logger.info(f"  - API 错误: {report['new_style']['api_errors']}")
    logger.info(f"\n改进:")
    logger.info(f"  - 成功率提升: {report['improvement']['success_rate']}")
    logger.info(f"  - 解析错误减少: {report['improvement']['parse_errors_reduced']}")
    logger.info(f"\n✅ 报告已保存: {report_file}")
    
    # 保存详细结果
    detail_file = Path("tmp/comparison_test/detailed_comparison.json")
    with open(detail_file, 'w', encoding='utf-8') as f:
        json.dump({
            "old_results": old_results,
            "new_results": new_results
        }, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✅ 详细对比已保存: {detail_file}")
    
    return report


async def main():
    """主函数"""
    logger = get_logger()
    
    old_batch_id = "batch_2033131099869949952"
    new_batch_id = "batch_2033131123887181824"
    
    logger.info("=" * 60)
    logger.info("开始监控批处理任务")
    logger.info("=" * 60)
    logger.info(f"旧方式: {old_batch_id}")
    logger.info(f"新方式: {new_batch_id}")
    logger.info("预计等待时间: 10-30 分钟")
    logger.info("=" * 60)
    
    # 并发监控两个任务
    old_task = asyncio.create_task(monitor_batch(old_batch_id, "old"))
    new_task = asyncio.create_task(monitor_batch(new_batch_id, "new"))
    
    # 等待两个任务都完成
    old_file, new_file = await asyncio.gather(old_task, new_task)
    
    if old_file and new_file:
        # 分析结果
        report = await analyze_results(old_file, new_file)
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ 对比测试完成！")
        logger.info("=" * 60)
        logger.info(f"\n请查看详细报告: tmp/comparison_test/comparison_report.json")
        logger.info(f"请查看详细对比: tmp/comparison_test/detailed_comparison.json")
    else:
        logger.error("❌ 批处理任务失败，无法进行对比")


if __name__ == "__main__":
    asyncio.run(main())
