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
        batch_extraction = schedule_config.get('batch_extraction', {})
        
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
        
        # 批量提取任务（每天运行一次，处理未处理的论文）
        batch_hour = batch_extraction.get('hour', 7)
        batch_minute = batch_extraction.get('minute', 0)
        
        self.scheduler.add_job(
            self.run_batch_extraction,
            CronTrigger(hour=batch_hour, minute=batch_minute),
            id='batch_extraction',
            name='批量提取任务',
            replace_existing=True
        )
        
        self.logger.info(f"批量提取已配置: {batch_hour:02d}:{batch_minute:02d}")
        
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
        from src.crawlers.pubmed_entrez import PubMedEntrezClient
        from src.crawlers.ncbi_id_converter import NCBIIDConverter
        from src.crawlers.jina_client import JinaClient
        from src.pipeline import LeadPipeline
        from src.exporters.csv_exporter import CSVExporter
        from src.db.utils import get_session
        from src.db.models import PaperLead, RawMarkdown
        from sqlalchemy import select
        
        self.logger.info("开始每日任务")
        start_time = datetime.now()
        
        try:
            # 1. 使用 PubMed Entrez API 搜索论文
            self.logger.info("开始 PubMed 论文搜索...")
            async with PubMedEntrezClient() as client:
                pmids = await client.search_papers(
                    terms=config.pubmed.search_terms,
                    days_back=7,
                    max_results=50
                )
            
            if not pmids:
                self.logger.info("没有找到符合条件的论文")
                return
            
            self.logger.info(f"找到 {len(pmids)} 篇论文")
            
            # 2. 转换 PMID → DOI
            async with NCBIIDConverter() as converter:
                pmid_doi_map = await converter.convert_batch(pmids)
            
            # 3. 过滤已存在的 DOI
            async with get_session() as session:
                result = await session.execute(
                    select(RawMarkdown.doi).where(RawMarkdown.doi.in_(pmid_doi_map.values()))
                )
                existing_dois = set(result.scalars().all())
            
            new_pmids = [pmid for pmid, doi in pmid_doi_map.items() if doi not in existing_dois]
            self.logger.info(f"过滤后剩余 {len(new_pmids)} 篇新论文")
            
            # 4. 获取 Markdown 内容
            async with JinaClient() as jina:
                for pmid in new_pmids:
                    doi = pmid_doi_map.get(pmid)
                    if not doi:
                        continue
                    
                    try:
                        # 构建 DOI URL
                        doi_url = f"https://doi.org/{doi}"
                        markdown = await jina.read(doi_url)
                        
                        # 存储到 raw_markdown 表
                        async with get_session() as session:
                            raw = RawMarkdown(
                                doi=doi,
                                pmid=pmid,
                                markdown_content=markdown,
                                source_url=doi_url,
                                processing_status='pending'
                            )
                            session.add(raw)
                            await session.commit()
                        
                        self.logger.info(f"论文已存储: doi={doi}, pmid={pmid}")
                    
                    except Exception as e:
                        self.logger.error(f"获取 Markdown 失败: doi={doi}, error={str(e)}")
            
            elapsed = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"每日任务完成, elapsed_seconds={elapsed:.1f}")
            
        except Exception as e:
            self.logger.error(f"每日任务失败", error=str(e))
            raise
    
    async def run_batch_extraction(self):
        """运行批量提取任务"""
        from src.pipeline_batch import BatchPipeline
        from src.notifiers.feishu import FeishuNotifier
        
        self.logger.info("开始批量提取任务")
        start_time = datetime.now()
        
        try:
            pipeline = BatchPipeline()
            
            # 运行批量提取（最多处理 100 篇）
            result = await pipeline.run_batch_extraction(
                limit=100,
                wait_for_completion=True,
                max_wait_minutes=60
            )
            
            # 发送飞书通知
            notifier = FeishuNotifier()
            await notifier.send_message(
                f"📊 批量提取完成\n\n"
                f"总论文数: {result['total_papers']}\n"
                f"成功: {result['successful']}\n"
                f"失败: {result['failed']}\n"
                f"批次ID: {result['batch_id']}\n"
                f"结果文件: {result.get('output_file', 'N/A')}"
            )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"批量提取完成, elapsed_seconds={elapsed:.1f}")
            
        except Exception as e:
            self.logger.error(f"批量提取失败", error=str(e))
            
            # 发送错误通知
            notifier = FeishuNotifier()
            await notifier.send_message(f"❌ 批量提取失败: {str(e)}")
            
            raise
    
    async def run_full_export(self):
        """运行全量导出"""
        from src.exporters.csv_exporter import CSVExporter
        from src.db.utils import get_session
        from src.db.models import PaperLead, TenderLead
        from sqlalchemy import select
        
        self.logger.info("开始全量导出")
        start_time = datetime.now()
        
        try:
            exporter = CSVExporter()
            
            # 1. 导出全量论文线索
            async with get_session() as session:
                result = await session.execute(
                    select(PaperLead)
                    .where(PaperLead.is_archived == False)
                    .order_by(PaperLead.score.desc().nullslast(), PaperLead.created_at.desc())
                )
                paper_leads = result.scalars().all()
            
            if paper_leads:
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
                        'change_marker': '',  # TODO: 实现 diff 标注
                    }
                    for l in paper_leads
                ]
                filepath = exporter.export_paper_leads(leads_data, include_diff=True)
                self.logger.info(f"论文全量导出完成: {filepath}, 共 {len(paper_leads)} 条")
            
            # 2. 导出全量招标线索
            async with get_session() as session:
                result = await session.execute(
                    select(TenderLead)
                    .where(TenderLead.is_archived == False)
                    .order_by(TenderLead.score.desc().nullslast(), TenderLead.created_at.desc())
                )
                tender_leads = result.scalars().all()
            
            if tender_leads:
                leads_data = [
                    {
                        'project_name': l.project_name,
                        'organization': l.organization,
                        'name': l.name,
                        'email': l.email,
                        'phone': l.phone,
                        'address': l.address,
                        'budget_info': l.budget_info,
                        'published_at': l.published_at,
                        'grade': l.grade,
                        'keywords_matched': l.keywords_matched,
                        'source_url': l.source_url,
                        'change_marker': '',  # TODO: 实现 diff 标注
                    }
                    for l in tender_leads
                ]
                filepath = exporter.export_tender_leads(leads_data, include_diff=True)
                self.logger.info(f"招标全量导出完成: {filepath}, 共 {len(tender_leads)} 条")
            
            elapsed = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"全量导出完成, elapsed_seconds={elapsed:.1f}")
            
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
