"""
Batch Monitor with Feishu Notifications
批量处理监控器（带飞书通知）
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from src.processors.batch_processor import BatchProcessor
from src.notifiers.feishu import FeishuNotifier
from src.logging_config import get_logger


class BatchMonitorWithNotification:
    """
    批量处理监控器（带飞书通知）
    
    负责：
    1. 健康检查
    2. 异常检测和告警
    3. 飞书通知
    4. 统计报告
    """
    
    def __init__(self):
        self.logger = get_logger()
        self.batch_processor = BatchProcessor()
        self.feishu = FeishuNotifier()
    
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
        
        # 2. 失败率检查
        total = sum(stats.values())
        if total > 0:
            failure_rate = (stats['failed'] / total) * 100
            if failure_rate > 20:
                issues.append(f"🔴 失败率过高: {failure_rate:.1f}%")
                status = 'error'
            elif failure_rate > 10:
                issues.append(f"⚠️ 失败率偏高: {failure_rate:.1f}%")
                status = 'warning'
        
        # 3. 积压检查
        if stats['pending'] > 100:
            issues.append(f"⚠️ 积压任务过多: {stats['pending']}")
            status = 'warning'
        
        # 4. 卡住任务检查
        stale_tasks = await self._check_stale_tasks()
        if stale_tasks > 0:
            issues.append(f"⚠️ 发现 {stale_tasks} 个卡住的任务")
            status = 'warning'
        
        return {
            'status': status,
            'stats': stats,
            'issues': issues,
            'checked_at': datetime.now().isoformat()
        }
    
    async def send_health_report(self):
        """发送健康报告到飞书"""
        health = await self.health_check()
        
        # 构建消息
        status_emoji = {
            'healthy': '✅',
            'warning': '⚠️',
            'error': '🔴'
        }
        
        emoji = status_emoji.get(health['status'], '❓')
        
        message = f"""{emoji} **批量处理健康报告**

**状态**: {health['status'].upper()}
**检查时间**: {health['checked_at']}

**统计数据**:
- 待处理: {health['stats']['pending']}
- 处理中: {health['stats']['processing']}
- 已完成: {health['stats']['completed']}
- 失败: {health['stats']['failed']}

**问题**:
{chr(10).join(f"- {issue}" for issue in health['issues']) if health['issues'] else "- 无问题"}
"""
        
        await self.feishu.send_message(message)
    
    async def send_batch_completion_notification(
        self,
        batch_id: str,
        total: int,
        successful: int,
        failed: int
    ):
        """发送批处理完成通知"""
        success_rate = (successful / total * 100) if total > 0 else 0
        
        status_emoji = "✅" if success_rate >= 80 else "⚠️" if success_rate >= 60 else "🔴"
        
        message = f"""{status_emoji} **批处理任务完成**

**任务ID**: {batch_id}
**总数**: {total}
**成功**: {successful}
**失败**: {failed}
**成功率**: {success_rate:.1f}%

**完成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        await self.feishu.send_message(message)
    
    async def send_error_alert(self, error_type: str, details: str):
        """发送错误告警"""
        message = f"""🔴 **批量处理错误告警**

**错误类型**: {error_type}
**详细信息**: {details}
**发生时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

请及时检查和处理。
"""
        
        await self.feishu.send_message(message)
    
    async def _check_stale_tasks(self, hours: int = 24) -> int:
        """检查卡住的任务数量"""
        from sqlalchemy import select, and_, func
        from src.db.models import RawMarkdown
        from src.db.utils import get_session
        
        threshold = datetime.utcnow() - timedelta(hours=hours)
        
        async with get_session() as session:
            result = await session.execute(
                select(func.count(RawMarkdown.id))
                .where(
                    and_(
                        RawMarkdown.processing_status == 'processing',
                        RawMarkdown.processed_at < threshold
                    )
                )
            )
            
            count = result.scalar()
            return count or 0
    
    async def auto_heal(self) -> Dict[str, int]:
        """
        自动修复：重置卡住的任务，重试失败的任务
        
        Returns:
            {
                'reset_stale': int,
                'retry_failed': int
            }
        """
        # 1. 重置卡住的任务
        reset_count = await self._reset_stale_tasks()
        
        # 2. 重试失败的任务
        retry_count = await self._retry_failed_tasks()
        
        result = {
            'reset_stale': reset_count,
            'retry_failed': retry_count
        }
        
        if reset_count > 0 or retry_count > 0:
            await self.feishu.send_message(
                f"🔧 **自动修复完成**\n\n"
                f"- 重置卡住任务: {reset_count}\n"
                f"- 重试失败任务: {retry_count}"
            )
        
        return result
    
    async def _reset_stale_tasks(self, hours: int = 24) -> int:
        """重置卡住的任务"""
        from sqlalchemy import update, and_
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
            
            return result.rowcount
    
    async def _retry_failed_tasks(self) -> int:
        """重试失败的任务"""
        from sqlalchemy import update
        from src.db.models import RawMarkdown
        from src.db.utils import get_session
        
        async with get_session() as session:
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
            
            return result.rowcount


# 全局监控器实例
batch_monitor = BatchMonitorWithNotification()
