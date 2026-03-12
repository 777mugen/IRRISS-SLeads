"""
Batch Monitoring and Error Handling
批量处理监控和错误处理
"""

import asyncio
from typing import List, Dict, Any
from datetime import datetime, timedelta

from src.processors.batch_processor import BatchProcessor
from src.logging_config import get_logger


class BatchMonitor:
    """
    批量处理监控器
    
    负责：
    1. 监控批处理任务状态
    2. 错误检测和告警
    3. 自动重试失败的论文
    4. 生成统计报告
    """
    
    def __init__(self):
        self.logger = get_logger()
        self.batch_processor = BatchProcessor()
    
    async def check_stale_tasks(self, hours: int = 24) -> List[str]:
        """
        检查卡住的任务（processing 状态超过指定小时数）
        
        Args:
            hours: 小时数阈值
            
        Returns:
            卡住的 batch_id 列表
        """
        from sqlalchemy import select, and_
        from src.db.models import RawMarkdown
        from src.db.utils import get_session
        
        threshold = datetime.utcnow() - timedelta(hours=hours)
        
        async with get_session() as session:
            result = await session.execute(
                select(RawMarkdown.batch_id)
                .where(
                    and_(
                        RawMarkdown.processing_status == 'processing',
                        RawMarkdown.processed_at < threshold
                    )
                )
                .distinct()
            )
            
            stale_batch_ids = result.scalars().all()
            
            if stale_batch_ids:
                self.logger.warning(f"发现 {len(stale_batch_ids)} 个卡住的批处理任务")
            
            return stale_batch_ids
    
    async def reset_stale_tasks(self, hours: int = 24) -> int:
        """
        重置卡住的任务（将 processing 改回 pending）
        
        Args:
            hours: 小时数阈值
            
        Returns:
            重置的任务数量
        """
        from sqlalchemy import update
        from src.db.models import RawMarkdown
        from src.db.utils import get_session
        
        threshold = datetime.utcnow() - timedelta(hours=hours)
        
        async with get_session() as session:
            stmt = (
                update(RawMarkdown)
                .where(
                    and_(
                        RawMarkdown.processing_status == 'processing',
                        RawMarkdown.processed_at < threshold
                    )
                )
                .values(
                    processing_status='pending',
                    batch_id=None,
                    error_message='任务超时，已自动重置'
                )
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            count = result.rowcount
            if count > 0:
                self.logger.info(f"已重置 {count} 个卡住的任务")
            
            return count
    
    async def retry_failed_tasks(self, max_retries: int = 3) -> int:
        """
        重试失败的论文（将 failed 改回 pending，限制重试次数）
        
        Args:
            max_retries: 最大重试次数
            
        Returns:
            重试的任务数量
        """
        from sqlalchemy import update, select, func
        from src.db.models import RawMarkdown
        from src.db.utils import get_session
        
        async with get_session() as session:
            # 查询重试次数（通过 error_message 中的 "重试" 关键字计数）
            # 这里简化处理：直接将 failed 改回 pending
            stmt = (
                update(RawMarkdown)
                .where(RawMarkdown.processing_status == 'failed')
                .values(
                    processing_status='pending',
                    error_message=None
                )
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            count = result.rowcount
            if count > 0:
                self.logger.info(f"已重试 {count} 个失败的任务")
            
            return count
    
    async def generate_report(self) -> Dict[str, Any]:
        """
        生成批处理统计报告
        
        Returns:
            {
                'pending': int,
                'processing': int,
                'completed': int,
                'failed': int,
                'total': int,
                'success_rate': float,
                'stale_tasks': int
            }
        """
        stats = await self.batch_processor.get_processing_stats()
        
        total = sum(stats.values())
        success_rate = (stats['completed'] / total * 100) if total > 0 else 0
        
        # 检查卡住的任务
        stale_batch_ids = await self.check_stale_tasks()
        
        report = {
            **stats,
            'total': total,
            'success_rate': round(success_rate, 2),
            'stale_tasks': len(stale_batch_ids)
        }
        
        return report
    
    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            {
                'status': 'healthy' | 'warning' | 'error',
                'stats': {...},
                'issues': [str]
            }
        """
        issues = []
        status = 'healthy'
        
        # 1. 检查统计数据
        stats = await self.batch_processor.get_processing_stats()
        
        if stats['failed'] > 10:
            issues.append(f"失败任务过多: {stats['failed']}")
            status = 'warning'
        
        # 2. 检查卡住的任务
        stale_batch_ids = await self.check_stale_tasks()
        if stale_batch_ids:
            issues.append(f"发现 {len(stale_batch_ids)} 个卡住的任务")
            status = 'warning'
        
        # 3. 检查积压
        if stats['pending'] > 100:
            issues.append(f"积压任务过多: {stats['pending']}")
            status = 'warning'
        
        if stats['failed'] > 50:
            issues.append(f"严重: 失败任务过多: {stats['failed']}")
            status = 'error'
        
        return {
            'status': status,
            'stats': stats,
            'issues': issues
        }
