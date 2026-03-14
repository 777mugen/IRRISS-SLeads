"""CSV 导入导出服务"""
import io
import csv
from typing import List, Dict, Any, Optional
from datetime import date
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import PaperLead, Feedback
from src.logging_config import get_logger

logger = get_logger()


class ExportService:
    """CSV 导入导出服务"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def export_full_csv(self, output_path: Path) -> int:
        """导出全量 CSV"""
        try:
            # 查询所有论文
            result = await self.session.execute(
                select(PaperLead).order_by(PaperLead.created_at.desc())
            )
            papers = result.scalars().all()
            
            # 准备数据
            data = []
            for paper in papers:
                data.append({
                    "DOI": paper.doi,
                    "PMID": paper.pmid,
                    "标题": paper.title,
                    "通讯作者": paper.name,
                    "邮箱": paper.email,
                    "电话": paper.phone,
                    "地址": paper.address,
                    "机构(中文)": paper.institution_cn,
                    "评分": paper.score,
                    "等级": paper.grade,
                    "反馈状态": paper.feedback_status,
                    "创建时间": paper.created_at.strftime("%Y-%m-%d %H:%M:%S") if paper.created_at else ""
                })
            
            # 使用 Pandas 导出
            df = pd.DataFrame(data)
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            
            logger.info("csv_exported", file=str(output_path), rows=len(data))
            return len(data)
            
        except Exception as e:
            logger.error("csv_export_failed", error=str(e))
            raise
    
    async def export_today_csv(self, output_path: Path) -> int:
        """导出今日新增 CSV"""
        try:
            today = date.today()
            tomorrow = date.today()
            
            # 查询今日新增
            result = await self.session.execute(
                select(PaperLead)
                .where(PaperLead.created_at >= today)
                .where(PaperLead.created_at < tomorrow)
                .order_by(PaperLead.created_at.desc())
            )
            papers = result.scalars().all()
            
            # 准备数据
            data = []
            for paper in papers:
                data.append({
                    "DOI": paper.doi,
                    "标题": paper.title,
                    "通讯作者": paper.name,
                    "邮箱": paper.email,
                    "评分": paper.grade,
                    "创建时间": paper.created_at.strftime("%Y-%m-%d %H:%M:%S") if paper.created_at else ""
                })
            
            # 使用 Pandas 导出
            df = pd.DataFrame(data)
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            
            logger.info("today_csv_exported", file=str(output_path), rows=len(data))
            return len(data)
            
        except Exception as e:
            logger.error("today_csv_export_failed", error=str(e))
            raise
    
    async def import_feedback_csv(self, csv_content: str) -> Dict[str, Any]:
        """导入反馈 CSV（预览）"""
        try:
            # 解析 CSV
            df = pd.read_csv(io.StringIO(csv_content))
            
            # 验证必需列
            required_columns = ["DOI", "线索准确性", "需求匹配度", "联系方式有效性", "成交速度", "成交价格"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(f"缺少必需列: {', '.join(missing_columns)}")
            
            # 统计
            total_rows = len(df)
            matched_dois = []
            unmatched_dois = []
            
            # 检查 DOI 是否存在
            for doi in df["DOI"]:
                result = await self.session.execute(
                    select(PaperLead.id).where(PaperLead.doi == doi)
                )
                if result.scalar():
                    matched_dois.append(doi)
                else:
                    unmatched_dois.append(doi)
            
            logger.info("feedback_csv_parsed", 
                       total=total_rows, 
                       matched=len(matched_dois),
                       unmatched=len(unmatched_dois))
            
            return {
                "total_rows": total_rows,
                "matched_count": len(matched_dois),
                "unmatched_count": len(unmatched_dois),
                "matched_dois": matched_dois[:10],  # 只显示前10个
                "unmatched_dois": unmatched_dois[:10],  # 只显示前10个
                "preview_data": df.head(5).to_dict('records')  # 预览前5行
            }
            
        except Exception as e:
            logger.error("feedback_csv_parse_failed", error=str(e))
            raise
    
    async def confirm_import_feedback(
        self, 
        csv_content: str,
        skip_unmatched: bool = True
    ) -> Dict[str, int]:
        """确认导入反馈数据"""
        try:
            # 解析 CSV
            df = pd.read_csv(io.StringIO(csv_content))
            
            imported_count = 0
            skipped_count = 0
            
            # 逐行导入
            for _, row in df.iterrows():
                doi = row["DOI"]
                
                # 查找论文
                result = await self.session.execute(
                    select(PaperLead.id).where(PaperLead.doi == doi)
                )
                paper_id = result.scalar()
                
                if not paper_id:
                    if skip_unmatched:
                        skipped_count += 1
                        continue
                    else:
                        raise ValueError(f"DOI 不存在: {doi}")
                
                # 创建反馈记录
                feedback = Feedback(
                    paper_lead_id=paper_id,
                    accuracy=row["线索准确性"],
                    demand_match=row["需求匹配度"],
                    contact_validity=row["联系方式有效性"],
                    deal_speed=row["成交速度"],
                    deal_price=row["成交价格"],
                    notes=row.get("备注", "")
                )
                
                self.session.add(feedback)
                imported_count += 1
            
            # 提交事务
            await self.session.commit()
            
            logger.info("feedback_imported", 
                       imported=imported_count,
                       skipped=skipped_count)
            
            return {
                "imported": imported_count,
                "skipped": skipped_count
            }
            
        except Exception as e:
            await self.session.rollback()
            logger.error("feedback_import_failed", error=str(e))
            raise
