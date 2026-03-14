"""
失败重试机制
为批处理系统添加自动重试功能
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import select, and_, update

from src.db.models import RawMarkdown
from src.db.utils import get_session
from src.logging_config import get_logger


class RetryManager:
    """失败重试管理器"""
    
    def __init__(self, max_retries: int = 3):
        self.logger = get_logger()
        self.max_retries = max_retries
    
    async def get_failed_papers(
        self, 
        limit: int = 50,
        min_retry_after_hours: int = 1
    ) -> List[RawMarkdown]:
        """
        获取可重试的失败论文
        
        Args:
            limit: 最多获取多少条
            min_retry_after_hours: 失败后多久可以重试（小时）
            
        Returns:
            可重试的论文列表
        """
        async with get_session() as session:
            # 计算重试时间阈值
            retry_threshold = datetime.utcnow() - timedelta(hours=min_retry_after_hours)
            
            query = select(RawMarkdown).where(
                and_(
                    RawMarkdown.processing_status == 'failed',
                    RawMarkdown.retry_count < self.max_retries,
                    RawMarkdown.processed_at < retry_threshold  # 避免频繁重试
                )
            ).order_by(
                RawMarkdown.processed_at.asc()  # 优先重试失败时间较长的
            ).limit(limit)
            
            result = await session.execute(query)
            papers = result.scalars().all()
            
            self.logger.info(f"找到 {len(papers)} 篇可重试的失败论文")
            return papers
    
    async def mark_for_retry(self, papers: List[RawMarkdown]):
        """
        标记论文为待重试状态
        
        Args:
            papers: 论文列表
        """
        async with get_session() as session:
            doi_list = [paper.doi for paper in papers]
            
            stmt = (
                update(RawMarkdown)
                .where(RawMarkdown.doi.in_(doi_list))
                .values(
                    processing_status='pending',  # 重置为 pending
                    retry_count=RawMarkdown.retry_count + 1,
                    last_retry_at=datetime.utcnow()
                )
                .execution_options(synchronize_session=False)
            )
            
            await session.execute(stmt)
            await session.commit()
            
            self.logger.info(f"已标记 {len(papers)} 篇论文为待重试状态")
    
    async def get_retry_stats(self) -> dict:
        """
        获取重试统计信息
        
        Returns:
            {
                'failed_no_retry': int,  # 失败但可重试
                'failed_max_retries': int,  # 已达最大重试次数
                'total_retries': int  # 总重试次数
            }
        """
        async with get_session() as session:
            from sqlalchemy import func
            
            # 失败且未达最大重试次数
            query1 = select(func.count(RawMarkdown.id)).where(
                and_(
                    RawMarkdown.processing_status == 'failed',
                    RawMarkdown.retry_count < self.max_retries
                )
            )
            result1 = await session.execute(query1)
            failed_no_retry = result1.scalar()
            
            # 失败且已达最大重试次数
            query2 = select(func.count(RawMarkdown.id)).where(
                and_(
                    RawMarkdown.processing_status == 'failed',
                    RawMarkdown.retry_count >= self.max_retries
                )
            )
            result2 = await session.execute(query2)
            failed_max_retries = result2.scalar()
            
            # 总重试次数
            query3 = select(func.sum(RawMarkdown.retry_count)).where(
                RawMarkdown.retry_count > 0
            )
            result3 = await session.execute(query3)
            total_retries = result3.scalar() or 0
            
            return {
                'failed_no_retry': failed_no_retry,
                'failed_max_retries': failed_max_retries,
                'total_retries': total_retries
            }


# 使用示例
async def retry_failed_papers():
    """重试失败的论文"""
    retry_manager = RetryManager(max_retries=3)
    
    # 1. 获取可重试的论文
    papers = await retry_manager.get_failed_papers(limit=50)
    
    if not papers:
        print("没有可重试的论文")
        return
    
    # 2. 标记为待重试
    await retry_manager.mark_for_retry(papers)
    
    # 3. 运行批处理（会自动处理 pending 状态的论文）
    from src.pipeline_batch import BatchPipeline
    pipeline = BatchPipeline()
    
    result = await pipeline.run_batch_extraction(
        limit=len(papers),
        wait_for_completion=True
    )
    
    print(f"重试结果: {result}")
    
    # 4. 获取重试统计
    stats = await retry_manager.get_retry_stats()
    print(f"重试统计: {stats}")
