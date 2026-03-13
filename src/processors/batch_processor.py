"""
Batch Processor
批量处理器

负责从数据库读取未处理的论文，构建 JSONL 文件供智谱批量 API 使用
"""

import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from sqlalchemy import select, and_
from sqlalchemy.dialects.postgresql import insert

from src.db.models import RawMarkdown
from src.db.utils import get_session
from src.config import config
from src.logging_config import get_logger


# 使用完整版 Prompt（从 prompts 模块导入）
from src.prompts.batch_extraction import BATCH_EXTRACTION_PROMPT_V1


class BatchProcessor:
    """
    批量处理器
    
    负责从数据库读取未处理的论文，构建 JSONL 文件
    """
    
    def __init__(self):
        self.logger = get_logger()
    
    async def get_unprocessed_papers(
        self, 
        limit: int = 100,
        batch_id: Optional[str] = None
    ) -> List[RawMarkdown]:
        """
        获取未处理的论文
        
        Args:
            limit: 最多获取多少条
            batch_id: 如果指定，只获取该批次的论文
            
        Returns:
            未处理的论文列表
        """
        async with get_session() as session:
            query = select(RawMarkdown).where(
                RawMarkdown.processing_status == 'pending'
            )
            
            if batch_id:
                query = query.where(RawMarkdown.batch_id == batch_id)
            
            query = query.limit(limit)
            
            result = await session.execute(query)
            papers = result.scalars().all()
            
            self.logger.info(f"找到 {len(papers)} 篇未处理论文")
            return papers
    
    async def build_batch_file(
        self, 
        papers: List[RawMarkdown],
        output_dir: Path = Path("tmp/batch")
    ) -> Path:
        """
        构建 JSONL 批处理文件
        
        Args:
            papers: 论文列表
            output_dir: 输出目录
            
        Returns:
            生成的 JSONL 文件路径
        """
        if not papers:
            raise ValueError("论文列表为空")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"batch_{timestamp}.jsonl"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for paper in papers:
                # 构建 JSONL 请求（双 role 结构：system + user）
                request = {
                    "custom_id": f"doi_{paper.doi.replace('/', '_')}",
                    "method": "POST",
                    "url": "/v4/chat/completions",
                    "body": {
                        "model": "glm-4-plus",
                        "messages": [
                            {
                                "role": "system",
                                "content": "你是一个专业的学术论文信息提取助手。严格按照规则提取，返回 JSON 格式。"
                            },
                            {
                                "role": "user",
                                "content": BATCH_EXTRACTION_PROMPT_V1.format(
                                    markdown_content=paper.markdown_content
                                )
                            }
                        ],
                        "temperature": 0.1,
                        "max_tokens": 4096
                    }
                }
                
                f.write(json.dumps(request, ensure_ascii=False) + '\n')
        
        self.logger.info(f"批处理文件已创建: {output_file}，包含 {len(papers)} 个请求")
        return output_file
    
    async def mark_as_processing(
        self, 
        papers: List[RawMarkdown], 
        batch_id: str
    ):
        """
        标记论文为处理中（批量优化）
        
        Args:
            papers: 论文列表
            batch_id: 批处理任务 ID
        """
        from sqlalchemy import update
        
        async with get_session() as session:
            doi_list = [paper.doi for paper in papers]
            
            # 批量更新（使用 synchronize_session=False 提升性能）
            stmt = (
                update(RawMarkdown)
                .where(RawMarkdown.doi.in_(doi_list))
                .values(
                    processing_status='processing',
                    batch_id=batch_id
                )
                .execution_options(synchronize_session=False)  # 性能优化
            )
            
            await session.execute(stmt)
            await session.commit()
            
            self.logger.info(f"已标记 {len(papers)} 篇论文为 processing 状态，batch_id={batch_id}")
    
    async def mark_as_completed(
        self, 
        doi: str,
        extracted_data: dict
    ):
        """
        标记论文处理完成
        
        Args:
            doi: DOI
            extracted_data: 提取的数据（用于更新 paper_leads）
        """
        from sqlalchemy import update
        
        async with get_session() as session:
            stmt = (
                update(RawMarkdown)
                .where(RawMarkdown.doi == doi)
                .values(
                    processing_status='completed',
                    processed_at=datetime.utcnow()
                )
            )
            
            await session.execute(stmt)
            await session.commit()
            
            self.logger.info(f"论文 {doi} 已标记为 completed")
    
    async def mark_as_failed(
        self, 
        doi: str, 
        error_message: str
    ):
        """
        标记论文处理失败
        
        Args:
            doi: DOI
            error_message: 错误信息
        """
        from sqlalchemy import update
        
        async with get_session() as session:
            stmt = (
                update(RawMarkdown)
                .where(RawMarkdown.doi == doi)
                .values(
                    processing_status='failed',
                    error_message=error_message,
                    processed_at=datetime.utcnow()
                )
            )
            
            await session.execute(stmt)
            await session.commit()
            
            self.logger.error(f"论文 {doi} 标记为 failed: {error_message}")
    
    async def get_processing_stats(self) -> dict:
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
        async with get_session() as session:
            from sqlalchemy import func
            
            query = select(
                RawMarkdown.processing_status,
                func.count(RawMarkdown.id)
            ).group_by(RawMarkdown.processing_status)
            
            result = await session.execute(query)
            stats = dict(result.all())
            
            # 确保所有状态都有值
            return {
                'pending': stats.get('pending', 0),
                'processing': stats.get('processing', 0),
                'completed': stats.get('completed', 0),
                'failed': stats.get('failed', 0)
            }
