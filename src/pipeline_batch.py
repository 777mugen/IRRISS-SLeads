"""
Batch Pipeline
批量处理管道

协调批量处理的完整流程
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from src.processors.batch_processor import BatchProcessor
from src.processors.batch_result_parser import BatchResultParser
from src.llm.batch_client import ZhiPuBatchClient
from src.db.models import PaperLead
from src.db.utils import get_session
from src.logging_config import get_logger


class BatchPipeline:
    """
    批量处理管道
    
    协调完整的批量处理流程：
    1. 读取未处理论文
    2. 构建 JSONL 文件
    3. 上传到智谱
    4. 创建批处理任务
    5. 等待完成
    6. 下载结果
    7. 解析并更新数据库
    """
    
    def __init__(self):
        self.logger = get_logger()
        self.batch_processor = BatchProcessor()
        self.result_parser = BatchResultParser()
    
    async def run_batch_extraction(
        self, 
        limit: int = 100,
        wait_for_completion: bool = True,
        max_wait_minutes: int = 60
    ) -> Dict[str, Any]:
        """
        运行批量提取
        
        Args:
            limit: 最多处理多少篇论文
            wait_for_completion: 是否等待完成
            max_wait_minutes: 最大等待时间（分钟）
            
        Returns:
            {
                'batch_id': str,
                'status': str,
                'total_papers': int,
                'successful': int,
                'failed': int,
                'output_file': str
            }
        """
        self.logger.info(f"开始批量提取，limit={limit}")
        
        # Step 1: 获取未处理论文
        papers = await self.batch_processor.get_unprocessed_papers(limit=limit)
        
        if not papers:
            self.logger.info("没有未处理的论文")
            return {
                'batch_id': None,
                'status': 'no_papers',
                'total_papers': 0,
                'successful': 0,
                'failed': 0,
                'output_file': None
            }
        
        # Step 2: 构建 JSONL 文件
        batch_file = await self.batch_processor.build_batch_file(papers)
        
        # Step 3: 上传并创建批处理任务
        async with ZhiPuBatchClient() as client:
            # 上传文件
            file_id = await client.upload_file(batch_file)
            self.logger.info(f"文件已上传: file_id={file_id}")
            
            # 创建批处理任务
            batch_id = await client.create_batch(file_id)
            self.logger.info(f"批处理任务已创建: batch_id={batch_id}")
            
            # 标记论文为 processing
            await self.batch_processor.mark_as_processing(papers, batch_id)
            
            if not wait_for_completion:
                return {
                    'batch_id': batch_id,
                    'status': 'submitted',
                    'total_papers': len(papers),
                    'successful': 0,
                    'failed': 0,
                    'output_file': None
                }
            
            # Step 4: 等待完成
            self.logger.info(f"等待批处理完成（最多 {max_wait_minutes} 分钟）...")
            batch = await client.wait_for_completion(
                batch_id,
                poll_interval=30,
                max_wait=max_wait_minutes * 60
            )
            
            # Step 5: 下载结果
            output_file_id = batch.get('output_file_id')
            if not output_file_id:
                raise Exception("批处理任务完成但没有输出文件")
            
            output_path = Path(f"tmp/batch/results_{batch_id}.jsonl")
            await client.download_result(output_file_id, output_path)
            self.logger.info(f"结果已下载: {output_path}")
            
            # Step 6: 解析结果并更新数据库
            results = self.result_parser.parse_result_file(output_path)
            summary = self.result_parser.get_summary(results)
            
            await self._process_results(results)
            
            return {
                'batch_id': batch_id,
                'status': 'completed',
                'total_papers': len(papers),
                'successful': summary['success'],
                'failed': summary['failed'] + summary['parse_error'],
                'output_file': str(output_path)
            }
    
    async def check_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """
        查询批处理任务状态
        
        Args:
            batch_id: 批处理任务 ID
            
        Returns:
            任务状态信息
        """
        async with ZhiPuBatchClient() as client:
            batch = await client.get_batch(batch_id)
            
            return {
                'batch_id': batch.get('id'),
                'status': batch.get('status'),
                'total': batch.get('total'),
                'completed': batch.get('completed'),
                'failed': batch.get('failed'),
                'created_at': batch.get('created_at'),
                'completed_at': batch.get('completed_at')
            }
    
    async def process_batch_results(self, batch_id: str) -> Dict[str, Any]:
        """
        处理已完成的批处理任务结果
        
        Args:
            batch_id: 批处理任务 ID
            
        Returns:
            处理结果摘要
        """
        async with ZhiPuBatchClient() as client:
            # 获取任务信息
            batch = await client.get_batch(batch_id)
            
            if batch.get('status') != 'completed':
                raise Exception(f"批处理任务未完成: status={batch.get('status')}")
            
            # 下载结果文件
            output_file_id = batch.get('output_file_id')
            if not output_file_id:
                raise Exception("没有输出文件")
            
            output_path = Path(f"tmp/batch/results_{batch_id}.jsonl")
            await client.download_result(output_file_id, output_path)
            
            # 解析结果
            results = self.result_parser.parse_result_file(output_path)
            summary = self.result_parser.get_summary(results)
            
            # 更新数据库
            await self._process_results(results)
            
            return {
                'batch_id': batch_id,
                'total_papers': len(results),
                'successful': summary['success'],
                'failed': summary['failed'] + summary['parse_error'],
                'output_file': str(output_path)
            }
    
    async def _process_results(self, results: list):
        """
        处理解析后的结果，更新数据库
        
        Args:
            results: 解析后的结果列表
        """
        for result in results:
            doi = result.get('doi')
            status = result.get('status')
            
            if not doi:
                self.logger.warning(f"结果缺少 DOI: {result}")
                continue
            
            if status == 'success':
                # 更新 paper_leads 表
                data = result.get('data')
                if data:
                    await self._update_paper_lead(doi, data)
                
                # 标记为完成
                await self.batch_processor.mark_as_completed(doi, data)
            
            else:
                # 标记为失败
                error = result.get('error', 'Unknown error')
                await self.batch_processor.mark_as_failed(doi, error)
    
    async def _update_paper_lead(self, doi: str, data: dict):
        """
        更新 paper_leads 表
        
        Args:
            doi: DOI
            data: 提取的数据
        """
        async with get_session() as session:
            from sqlalchemy import update
            
            corr_author = data.get('corresponding_author', {})
            
            stmt = (
                update(PaperLead)
                .where(PaperLead.doi == doi)
                .values(
                    title=data.get('title'),
                    published_at=data.get('published_at'),
                    name=corr_author.get('name'),
                    email=corr_author.get('email'),
                    phone=corr_author.get('phone'),
                    institution=corr_author.get('institution'),
                    institution_cn=corr_author.get('institution_cn'),
                    address=corr_author.get('address'),
                    address_cn=corr_author.get('address_cn'),
                    all_authors=data.get('all_authors_info')
                )
            )
            
            await session.execute(stmt)
            await session.commit()
            
            self.logger.info(f"已更新 paper_leads: doi={doi}")
    
    async def get_processing_stats(self) -> Dict[str, int]:
        """
        获取处理统计信息
        
        Returns:
            {
                'pending': int,
                'processing': int,
                'completed': int,
                'failed': int
            }
        """
        return await self.batch_processor.get_processing_stats()
