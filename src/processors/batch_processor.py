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


# 批量提取的 Prompt 模板
BATCH_EXTRACTION_PROMPT = """从以下论文内容中提取信息，以 JSON 格式返回。

**🔴 重要说明 - 必须严格遵守**：

1. **绝对不要提取 References 部分的任何信息**：
   - References 中的作者姓名、单位、联系方式
   - References 中的文章标题、DOI
   - References 中的任何其他信息
   
2. **只提取正文部分的信息**：
   - 论文标题（正文标题）
   - 发表时间
   - 通讯作者信息（正文中标注的）
   
3. **通讯作者识别标准**：
   - 寻找 "Correspondence to"、"Corresponding Author"、"通讯作者" 等标识
   - 只提取明确标注为通讯作者的人员信息
   - 不要提取其他作者或被引用文献作者的信息

4. **如果某个字段找不到，设为 null**

论文内容：
{markdown_content}

---

**返回格式（JSON）**：
{{
  "title": "文章标题（来自正文，非 References）",
  "published_at": "YYYY-MM-DD 或 null",
  "corresponding_author": {{
    "name": "通讯作者姓名（来自正文，非 References）",
    "email": "邮箱地址（来自正文，非 References）",
    "phone": "电话号码（来自正文，非 References）",
    "institution": "所属单位（来自正文，非 References）",
    "address": "单位地址（来自正文，非 References）"
  }}
}}

**只返回 JSON，不要有任何其他文字。**
"""


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
                # 构建 JSONL 请求
                request = {
                    "custom_id": f"doi_{paper.doi.replace('/', '_')}",
                    "method": "POST",
                    "url": "/v4/chat/completions",
                    "body": {
                        "model": "glm-4-plus",
                        "messages": [
                            {
                                "role": "user",
                                "content": BATCH_EXTRACTION_PROMPT.format(
                                    markdown_content=paper.markdown_content
                                )
                            }
                        ],
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
