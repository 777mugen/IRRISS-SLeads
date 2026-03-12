"""
Scheduler for daily tasks.
定时任务调度器。
"""

from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config import config
from src.logging_config import get_logger


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
        self.logger = get_logger()
    
    def setup_jobs(self):
        """配置定时任务"""
        schedule_config = config.scheduler
        daily = schedule_config.get('daily_run', {})
        full_export = schedule_config.get('full_export', {})
        
        # 每日任务
        hour = daily.get('hour', 6)
        minute = daily.get('minute', 0)
        
        self.scheduler.add_job(
            self.run_daily_task,
            CronTrigger(hour=hour, minute=minute),
            id='daily_task',
            name='每日线索抓取',
            replace_existing=True
        )
        
        self.logger.info(f"每日任务已配置: {hour:02d}:{minute:02d}")
        
        # 周日全量导出
        day_of_week = full_export.get('day_of_week', 'sun')
        full_hour = full_export.get('hour', 6)
        full_minute = full_export.get('minute', 0)
        
        self.scheduler.add_job(
            self.run_full_export,
            CronTrigger(day_of_week=day_of_week, hour=full_hour, minute=full_minute),
            id='full_export',
            name='周日全量导出',
            replace_existing=True
        )
        
        self.logger.info(f"全量导出已配置: 每周{day_of_week} {full_hour:02d}:{full_minute:02d}")
    
    async def run_daily_task(self):
        """运行每日任务"""
        from src.crawlers.pubmed import PubMedCrawler
        from src.pipeline import LeadPipeline
        from src.exporters.csv_exporter import CSVExporter
        from src.db.utils import get_session
        from src.db.models import PaperLead
        from sqlalchemy import select
        
        self.logger.info("开始每日任务")
        start_time = datetime.now()
        
        try:
            # 1. 论文爬取
            self.logger.info("开始 PubMed 论文爬取...")
            async with PubMedCrawler() as crawler:
                papers = await crawler.run(days_back=7, max_papers=50)
                
                if papers:
                    self.logger.info(f"抓取到 {len(papers)} 篇论文")
                    
                    # 2. 处理论文
                    pipeline = LeadPipeline()
                    processed = 0
                    for paper in papers:
                        if paper['status'] == 'success':
                                result = await pipeline.process_paper(
                                    paper['url'], 
                                    paper['content']
                                )
                                if result:
                                    processed += 1
                    
                    await pipeline.close()
                    self.logger.info(f"论文处理完成: {processed}/{len(papers)} 入库")
            
            # 3. 增量导出
            async with get_session() as session:
                # 获取今天新入库的线索
                today = datetime.now().date()
                result = await session.execute(
                    select(PaperLead)
                    .where(PaperLead.created_at >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))
                    .order_by(PaperLead.score.desc())
                )
                leads = result.scalars().all()
                
            if leads:
                exporter = CSVExporter()
                leads_data = [
                    {
                        'name': l.name,
                        'institution': l.institution,
                        'email': l.email,
                        'phone': l.phone,
                        'address': l.address,
                        'title': l.title,
                        'published_at': l.published_at,
                        'grade': l.grade,
                        'keywords_matched': l.keywords_matched,
                        'source_url': l.source_url,
                    }
                    for l in leads
                ]
                filepath = exporter.export_paper_leads(leads_data)
                self.logger.info(f"增量导出完成: {filepath}")
            
            elapsed = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"每日任务完成, elapsed_seconds={elapsed:.1f}")
            
        except Exception as e:
            self.logger.error(f"每日任务失败", error=str(e))
            raise
    
    async def run_full_export(self):
        """运行全量导出"""
        self.logger.info("开始全量导出")
        start_time = datetime.now()
        
        try:
            # TODO: 实现全量导出
            # 1. 同步数据库
            # 2. 导出全量 CSV
            # 3. 标注 diff
            
            elapsed = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"全量导出完成", elapsed_seconds=elapsed)
            
        except Exception as e:
            self.logger.error(f"全量导出失败", error=str(e))
            raise
    
    def start(self):
        """启动调度器"""
        self.setup_jobs()
        self.scheduler.start()
        self.logger.info("调度器已启动")
    
    def stop(self):
        """停止调度器"""
        self.scheduler.shutdown()
        self.logger.info("调度器已停止")


# 全局调度器实例
scheduler = TaskScheduler()
