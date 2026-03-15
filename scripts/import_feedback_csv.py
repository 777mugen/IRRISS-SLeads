#!/usr/bin/env python3
"""
销售反馈导入脚本（CSV 方式）

用法:
    python scripts/import_feedback_csv.py feedback.csv

CSV 格式:
    paper_lead_id,doi,线索准确性,需求匹配度,联系方式有效性,成交速度,成交价格,备注
    
示例:
    123,10.1016/j.jad.2026.121506,好,好,中,差,中,客户很感兴趣但预算有限
"""

import asyncio
import csv
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from src.db.models import PaperLead, Feedback
from src.db.utils import get_session
from src.logging_config import get_logger


logger = get_logger()


async def import_feedback_csv(csv_path: Path):
    """导入反馈 CSV"""
    
    if not csv_path.exists():
        logger.error(f"文件不存在: {csv_path}")
        return
    
    logger.info(f"开始导入反馈: {csv_path}")
    
    stats = {
        'total': 0,
        'success': 0,
        'not_found': 0,
        'duplicate': 0
    }
    
    async with get_session() as session:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                stats['total'] += 1
                
                try:
                    # 获取 paper_lead_id
                    paper_lead_id = int(row.get('paper_lead_id', 0))
                    
                    if not paper_lead_id:
                        # 尝试通过 DOI 查找
                        doi = row.get('doi', '').strip()
                        if doi:
                            result = await session.execute(
                                select(PaperLead.id).where(PaperLead.doi == doi)
                            )
                            lead = result.scalar_one_or_none()
                            if lead:
                                paper_lead_id = lead
                            else:
                                logger.warning(f"未找到 DOI: {doi}")
                                stats['not_found'] += 1
                                continue
                        else:
                            logger.warning(f"缺少 paper_lead_id 和 doi")
                            stats['not_found'] += 1
                            continue
                    
                    # 检查是否已有反馈
                    result = await session.execute(
                        select(Feedback).where(Feedback.paper_lead_id == paper_lead_id)
                    )
                    existing_feedback = result.scalar_one_or_none()
                    
                    if existing_feedback:
                        logger.warning(f"已存在反馈: paper_lead_id={paper_lead_id}，更新")
                        # 更新现有反馈
                        existing_feedback.accuracy = row.get('线索准确性', '').strip()
                        existing_feedback.demand_match = row.get('需求匹配度', '').strip()
                        existing_feedback.contact_validity = row.get('联系方式有效性', '').strip()
                        existing_feedback.deal_speed = row.get('成交速度', '').strip()
                        existing_feedback.deal_price = row.get('成交价格', '').strip()
                        existing_feedback.notes = row.get('备注', '').strip()
                        existing_feedback.updated_at = datetime.utcnow()
                        stats['duplicate'] += 1
                    else:
                        # 创建新反馈
                        feedback = Feedback(
                            paper_lead_id=paper_lead_id,
                            accuracy=row.get('线索准确性', '').strip(),
                            demand_match=row.get('需求匹配度', '').strip(),
                            contact_validity=row.get('联系方式有效性', '').strip(),
                            deal_speed=row.get('成交速度', '').strip(),
                            deal_price=row.get('成交价格', '').strip(),
                            notes=row.get('备注', '').strip()
                        )
                        session.add(feedback)
                    
                    # 更新 paper_leads 的 feedback_status
                    result = await session.execute(
                        select(PaperLead).where(PaperLead.id == paper_lead_id)
                    )
                    lead = result.scalar_one_or_none()
                    if lead:
                        lead.feedback_status = '已反馈'
                    
                    await session.commit()
                    stats['success'] += 1
                    
                except Exception as e:
                    logger.error(f"导入失败: {row}, 错误: {e}")
                    await session.rollback()
    
    # 打印统计
    logger.info(f"\n{'='*60}")
    logger.info(f"导入完成统计")
    logger.info(f"{'='*60}")
    logger.info(f"总记录数: {stats['total']}")
    logger.info(f"成功导入: {stats['success']}")
    logger.info(f"未找到: {stats['not_found']}")
    logger.info(f"更新已有: {stats['duplicate']}")
    logger.info(f"{'='*60}")


def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/import_feedback_csv.py <csv_file>")
        print("\nCSV 格式:")
        print("  paper_lead_id,doi,线索准确性,需求匹配度,联系方式有效性,成交速度,成交价格,备注")
        print("\n示例:")
        print("  123,10.1016/j.jad.2026.121506,好,好,中,差,中,客户很感兴趣但预算有限")
        sys.exit(1)
    
    csv_path = Path(sys.argv[1])
    asyncio.run(import_feedback_csv(csv_path))


if __name__ == "__main__":
    main()
