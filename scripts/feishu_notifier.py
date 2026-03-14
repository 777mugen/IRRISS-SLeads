"""
飞书通知系统
定期检查批处理失败情况，提炼共性，并飞书通知用户
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.processors.failure_analyzer import FailureAnalyzer
from src.logging_config import get_logger


class FeishuNotifier:
    """飞书通知器"""
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.logger = get_logger()
        self.webhook_url = webhook_url
    
    async def send_message(self, message: str):
        """
        发送飞书消息
        
        Args:
            message: 消息内容（Markdown 格式）
        """
        if not self.webhook_url:
            self.logger.warning("飞书 Webhook URL 未配置，跳过发送")
            return
        
        import aiohttp
        
        payload = {
            "msg_type": "interactive",
            "card": {
                "elements": [
                    {
                        "tag": "markdown",
                        "content": message
                    }
                ]
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        self.logger.info("飞书通知发送成功")
                    else:
                        self.logger.error(
                            f"飞书通知发送失败: {response.status}"
                        )
        
        except Exception as e:
            self.logger.error(f"飞书通知发送异常: {e}")
    
    async def notify_batch_failures(self):
        """
        检查并通知批处理失败情况
        
        功能：
        1. 检查失败论文
        2. 提炼共性和特征
        3. 发送飞书通知
        """
        self.logger.info("开始检查批处理失败情况...")
        
        # 1. 分析失败论文
        analyzer = FailureAnalyzer()
        report = await analyzer.generate_report()
        
        # 2. 检查是否需要通知
        if "没有失败的论文" in report:
            self.logger.info("没有失败的论文，不发送通知")
            return
        
        # 3. 发送飞书通知
        await self.send_message(report)
        
        self.logger.info("失败分析报告已发送")
    
    async def send_daily_summary(self):
        """
        发送每日摘要
        
        包括：
        - 处理统计
        - 失败情况
        - 改进建议
        """
        from src.pipeline_batch import BatchPipeline
        
        pipeline = BatchPipeline()
        stats = await pipeline.get_processing_stats()
        
        # 生成摘要
        summary_lines = [
            "# 📊 每日批处理摘要",
            "",
            f"**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## 处理统计",
            "",
            f"- ✅ **已完成**: {stats['completed']} 篇",
            f"- ⏳ **处理中**: {stats['processing']} 篇",
            f"- 📋 **待处理**: {stats['pending']} 篇",
            f"- ❌ **失败**: {stats['failed']} 篇",
            ""
        ]
        
        # 如果有失败，添加失败分析
        if stats['failed'] > 0:
            analyzer = FailureAnalyzer()
            papers = await analyzer.get_failed_papers(limit=10)
            
            summary_lines.extend([
                "## ⚠️ 最近失败论文",
                ""
            ])
            
            for i, paper in enumerate(papers[:5], 1):
                summary_lines.append(
                    f"{i}. **{paper.doi}**"
                )
                summary_lines.append(
                    f"   - 错误: {paper.error_message[:50] if paper.error_message else 'N/A'}"
                )
                summary_lines.append(
                    f"   - 重试: {paper.retry_count} 次"
                )
                summary_lines.append("")
            
            # 添加改进建议
            analysis = await analyzer.analyze_failures(papers)
            
            summary_lines.extend([
                "## 🔧 改进建议",
                ""
            ])
            
            for rec in analysis['recommendations'][:3]:
                summary_lines.append(f"- {rec}")
                summary_lines.append("")
        
        summary = "\n".join(summary_lines)
        
        # 发送通知
        await self.send_message(summary)
        
        self.logger.info("每日摘要已发送")


async def check_and_notify():
    """
    检查并通知（用于定时任务）
    
    逻辑：
    1. 检查失败论文
    2. 如果有达到最大重试次数的论文，立即通知
    3. 否则，每日发送摘要
    """
    analyzer = FailureAnalyzer()
    retry_stats = await analyzer.check_retry_attempts()
    
    notifier = FeishuNotifier()
    
    # 如果有需要人工复核的论文，立即通知
    if retry_stats['needs_manual_review']:
        await notifier.notify_batch_failures()
    else:
        # 否则，发送每日摘要
        await notifier.send_daily_summary()


async def main():
    """测试飞书通知"""
    notifier = FeishuNotifier()
    
    # 发送测试消息
    test_message = """
# 🧪 测试通知

这是一条测试消息，验证飞书通知功能是否正常。

- ✅ 测试项目 1
- ✅ 测试项目 2
- ✅ 测试项目 3
"""
    
    await notifier.send_message(test_message)
    
    print("✅ 测试通知已发送")


if __name__ == "__main__":
    asyncio.run(main())
