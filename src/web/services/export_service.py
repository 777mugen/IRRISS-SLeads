"""导出服务层"""
from typing import List, Dict, Any, Optional
from datetime import date, datetime
from pathlib import Path
import pandas as pd
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import PaperLead, Feedback
from src.logging_config import get_logger

logger = get_logger()


class ExportService:
    """导出服务"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_paper_leads_for_export(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        grade: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取论文线索用于导出"""
        try:
            query = select(PaperLead)
            
            # 日期筛选
            if start_date:
                query = query.where(PaperLead.created_at >= start_date)
            if end_date:
                query = query.where(PaperLead.created_at <= end_date)
            
            # 等级筛选
            if grade:
                query = query.where(PaperLead.grade == grade)
            
            query = query.order_by(PaperLead.created_at.desc())
            
            result = await self.session.execute(query)
            papers = result.scalars().all()
            
            # 转换为字典列表
            data = []
            for paper in papers:
                data.append({
                    'DOI': paper.doi or '',
                    'PMID': paper.pmid or '',
                    '标题': paper.title or '',
                    '通讯作者': paper.name or '',
                    '邮箱': paper.email or '',
                    '电话': paper.phone or '',
                    '地址（英文）': paper.address or '',
                    '地址（中文）': paper.address_cn or '',
                    '机构': paper.institution_cn or '',
                    '评分': paper.score or 0,
                    '等级': paper.grade or '',
                    '反馈状态': paper.feedback_status or '',
                    '创建时间': paper.created_at.strftime('%Y-%m-%d %H:%M:%S') if paper.created_at else ''
                })
            
            logger.info("paper_leads_exported", count=len(data))
            return data
        except Exception as e:
            logger.error("export_failed", error=str(e))
            raise
    
    async def get_today_papers(self) -> List[Dict[str, Any]]:
        """获取今日新增论文"""
        today = date.today()
        return await self.get_paper_leads_for_export(start_date=today)
    
    async def get_all_papers(self) -> List[Dict[str, Any]]:
        """获取所有论文"""
        return await self.get_paper_leads_for_export()
    
    async def import_feedback_csv(self, df: pd.DataFrame) -> Dict[str, Any]:
        """导入销售反馈 CSV"""
        try:
            stats = {
                'total': len(df),
                'matched': 0,
                'updated': 0,
                'not_found': 0,
                'errors': []
            }
            
            # 预览结果
            preview = []
            
            for idx, row in df.iterrows():
                doi = row.get('DOI', '').strip()
                
                if not doi:
                    stats['errors'].append(f"行 {idx + 1}: DOI 为空")
                    continue
                
                # 查找对应的 paper_lead
                query = select(PaperLead).where(PaperLead.doi == doi)
                result = await self.session.execute(query)
                paper = result.scalar_one_or_none()
                
                if not paper:
                    stats['not_found'] += 1
                    preview.append({
                        'doi': doi,
                        'status': 'not_found',
                        'message': 'DOI 不存在'
                    })
                    continue
                
                stats['matched'] += 1
                
                # 创建或更新反馈
                feedback_query = select(Feedback).where(Feedback.paper_lead_id == paper.id)
                feedback_result = await self.session.execute(feedback_query)
                feedback = feedback_result.scalar_one_or_none()
                
                if not feedback:
                    feedback = Feedback(paper_lead_id=paper.id)
                    self.session.add(feedback)
                
                # 更新反馈字段
                if '线索准确性' in row:
                    feedback.accuracy = row['线索准确性']
                if '需求匹配度' in row:
                    feedback.demand_match = row['需求匹配度']
                if '联系方式有效性' in row:
                    feedback.contact_validity = row['联系方式有效性']
                if '成交速度' in row:
                    feedback.deal_speed = row['成交速度']
                if '成交价格' in row:
                    feedback.deal_price = row['成交价格']
                if '备注' in row:
                    feedback.notes = row['备注']
                
                stats['updated'] += 1
                preview.append({
                    'doi': doi,
                    'status': 'success',
                    'message': '反馈已更新'
                })
            
            logger.info("feedback_import_complete", stats=stats)
            
            return {
                'stats': stats,
                'preview': preview[:10]  # 只返回前10条预览
            }
        except Exception as e:
            logger.error("import_failed", error=str(e))
            raise
