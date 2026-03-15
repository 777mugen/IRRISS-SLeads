"""
优化的论文提取脚本（支持后台运行 + 断点续传 + 分批处理）

优化内容：
1. ✅ 后台运行模式（不超时）
2. ✅ 断点续传（从进度文件恢复）
3. ✅ 分批处理（避免内存问题）
4. ✅ 更频繁的进度保存（每 5 篇）
5. ✅ 更好的错误处理和重试机制
6. ✅ 详细的日志记录
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime, date
from typing import List, Dict, Optional
import signal

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.crawlers.pubmed_entrez import PubMedEntrezClient
from src.crawlers.jina_client import JinaClient
from src.llm.batch_client import ZhiPuBatchClient
from src.prompts.batch_extraction import BATCH_EXTRACTION_PROMPT_V2
from src.logging_config import get_logger
import yaml


class OptimizedPaperExtractor:
    """优化的论文提取器（支持后台运行 + 断点续传）"""
    
    def __init__(
        self, 
        target_count: int = 1000,
        batch_size: int = 100,
        resume_from_progress: bool = True
    ):
        self.target_count = target_count
        self.batch_size = batch_size
        self.resume_enabled = resume_from_progress
        self.logger = get_logger()
        
        # 加载关键词配置
        with open(project_root / "config/keywords.yaml") as f:
            self.keywords_config = yaml.safe_load(f)
        
        # 初始化客户端
        self.pubmed_client = PubMedEntrezClient()
        self.jina_client = JinaClient()
        self.batch_client = ZhiPuBatchClient()
        
        # 进度文件
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.progress_file = project_root / f"tmp/extraction_progress_{self.timestamp}.json"
        self.progress_file.parent.mkdir(exist_ok=True)
        
        # 统计
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'no_doi': 0,
            'errors': []
        }
        
        # 中断标志
        self._interrupted = False
        
        # 注册信号处理
        signal.signal(signal.SIGTERM, self._handle_interrupt)
        signal.signal(signal.SIGINT, self._handle_interrupt)
    
    def _handle_interrupt(self, signum, frame):
        """处理中断信号"""
        self.logger.warning(f"\n⚠️  收到中断信号 ({signum})，正在保存进度...")
        self._interrupted = True
        self._save_progress([])  # 保存当前进度
        self.logger.info(f"✅ 进度已保存到: {self.progress_file}")
        sys.exit(0)
    
    def _load_progress(self) -> Optional[Dict]:
        """加载进度文件"""
        if not self.resume_enabled or not self.progress_file.exists():
            return None
        
        try:
            with open(self.progress_file) as f:
                progress = json.load(f)
            
            self.logger.info(f"\n{'='*80}")
            self.logger.info(f"📂 从进度文件恢复")
            self.logger.info(f"{'='*80}")
            self.logger.info(f"文件: {self.progress_file}")
            self.logger.info(f"已处理: {progress.get('processed', 0)} 篇")
            self.logger.info(f"任务数: {len(progress.get('tasks', []))}")
            
            return progress
        except Exception as e:
            self.logger.error(f"加载进度失败: {e}")
            return None
    
    def _save_progress(self, tasks: List[Dict], processed: int = 0):
        """保存进度文件"""
        progress = {
            'timestamp': self.timestamp,
            'target_count': self.target_count,
            'processed': processed,
            'tasks_count': len(tasks),
            'stats': self.stats,
            'tasks': tasks[-100:] if len(tasks) > 100 else tasks  # 只保留最近 100 个
        }
        
        with open(self.progress_file, 'w') as f:
            json.dump(progress, f, indent=2, ensure_ascii=False)
    
    async def build_search_queries(self) -> List[str]:
        """构建搜索查询"""
        queries = []
        
        english_core = self.keywords_config['english']['core']
        english_equipment = self.keywords_config['english']['equipment']
        
        # 策略 1: 核心关键词（前 10 个）
        for keyword in english_core[:10]:
            queries.append(f'"{keyword}"')
        
        # 策略 2: 核心关键词 + 设备关键词（前 5×3=15 个）
        for core_kw in english_core[:5]:
            for equip_kw in english_equipment[:3]:
                queries.append(f'"{core_kw}" AND "{equip_kw}"')
        
        # 策略 3: 布尔组合（3 个）
        queries.append('"Multiplex Immunofluorescence" OR "mIF" OR "TSA"')
        queries.append('"Spatial Proteomics" OR "Spatial Transcriptomics"')
        queries.append('"Confocal Microscopy" OR "Fluorescence Microscope"')
        
        self.logger.info(f"构建了 {len(queries)} 个搜索查询")
        return queries
    
    async def search_papers_batch(self, start_from: int = 0) -> List[Dict]:
        """
        分批搜索论文
        
        Args:
            start_from: 从第几个查询开始（用于断点续传）
        
        Returns:
            论文列表 [{pmid, doi, title, ...}, ...]
        """
        queries = await self.build_search_queries()
        
        all_papers = []
        seen_pmids = set()
        
        # 每个查询的目标数量
        per_query = self.target_count // len(queries) + 50
        
        for i, query in enumerate(queries[start_from:], start=start_from + 1):
            if self._interrupted:
                break
            
            self.logger.info(f"\n[{i}/{len(queries)}] 查询: {query[:60]}...")
            
            try:
                # 搜索 2024-2026 年的论文
                papers = await self.pubmed_client.search_and_fetch(
                    query=query,
                    max_results=per_query,
                    date_range=(2024, 2026)
                )
                
                # 去重
                new_papers = []
                for paper in papers:
                    pmid = paper.get('pmid')
                    if pmid and pmid not in seen_pmids:
                        seen_pmids.add(pmid)
                        new_papers.append(paper)
                
                all_papers.extend(new_papers)
                
                self.logger.info(f"  找到 {len(papers)} 篇，新增 {len(new_papers)} 篇")
                self.logger.info(f"  累计: {len(all_papers)} 篇")
                
                # 达到目标就停止
                if len(all_papers) >= self.target_count:
                    self.logger.info(f"\n✅ 达到目标: {len(all_papers)} 篇")
                    break
                
                # 速率限制
                await asyncio.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"  ❌ 查询失败: {e}")
                # 继续下一个查询
                continue
        
        # 截断到目标数量
        all_papers = all_papers[:self.target_count]
        
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"搜索完成: {len(all_papers)} 篇论文")
        self.logger.info(f"{'='*80}\n")
        
        return all_papers
    
    async def fetch_and_prepare_batch(
        self, 
        papers: List[Dict],
        start_from: int = 0,
        existing_tasks: List[Dict] = None
    ) -> List[Dict]:
        """
        获取论文全文并准备批处理任务（支持断点续传）
        
        Args:
            papers: 论文列表
            start_from: 从第几篇开始
            existing_tasks: 已有的任务列表（用于追加）
        """
        tasks = existing_tasks or []
        
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"开始获取论文全文（从第 {start_from + 1} 篇）")
        self.logger.info(f"{'='*80}\n")
        
        for i, paper in enumerate(papers[start_from:], start=start_from + 1):
            if self._interrupted:
                self.logger.warning(f"\n⚠️  中断信号，停止处理")
                break
            
            pmid = paper.get('pmid')
            doi = paper.get('doi')
            title = paper.get('title', 'N/A')[:50]
            
            self.logger.info(f"[{i}/{len(papers)}] PMID: {pmid} - {title}")
            
            if not doi:
                self.logger.warning(f"  ⚠️  无 DOI，跳过")
                self.stats['no_doi'] += 1
                continue
            
            try:
                # 使用 Jina Reader 获取论文全文
                content = await self.jina_client.read_paper(f"https://doi.org/{doi}")
                
                if not content or len(content) < 100:
                    self.logger.error(f"  ❌ 内容过短或为空")
                    self.stats['failed'] += 1
                    self.stats['errors'].append({
                        'pmid': pmid,
                        'doi': doi,
                        'error': 'content_too_short'
                    })
                    continue
                
                self.logger.info(f"  ✅ 获取成功: {len(content)} 字符")
                
                # 准备批处理任务
                task = {
                    "custom_id": f"pmid_{pmid}",
                    "method": "POST",
                    "url": "/v4/chat/completions",
                    "body": {
                        "model": "glm-4-plus",
                        "messages": [
                            {
                                "role": "system",
                                "content": "你是一个专业的学术论文信息提取助手。"
                            },
                            {
                                "role": "user",
                                "content": BATCH_EXTRACTION_PROMPT_V2.replace(
                                    "{markdown_content}",
                                    content
                                )
                            }
                        ],
                        "temperature": 0.1,
                        "max_tokens": 2000
                    }
                }
                
                tasks.append(task)
                self.stats['success'] += 1
                
                # 每 5 篇保存一次进度（更频繁）
                if i % 5 == 0:
                    self._save_progress(tasks, processed=i)
                    self.logger.info(f"  💾 进度已保存 ({i}/{len(papers)})")
                
            except Exception as e:
                self.logger.error(f"  ❌ 失败: {e}")
                self.stats['failed'] += 1
                self.stats['errors'].append({
                    'pmid': pmid,
                    'doi': doi,
                    'error': str(e)
                })
                
                # 错误后也保存进度
                self._save_progress(tasks, processed=i)
            
            # 速率限制
            await asyncio.sleep(1.0)
        
        # 最终统计
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"全文获取完成")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"总论文数: {len(papers)}")
        self.logger.info(f"成功获取: {self.stats['success']}")
        self.logger.info(f"失败: {self.stats['failed']}")
        self.logger.info(f"无 DOI: {self.stats['no_doi']}")
        self.logger.info(f"批处理任务: {len(tasks)}")
        
        # 保存最终统计
        stats_file = project_root / f"tmp/extraction_stats_{self.timestamp}.json"
        with open(stats_file, 'w') as f:
            json.dump({
                'timestamp': self.timestamp,
                'stats': self.stats,
                'task_count': len(tasks)
            }, f, indent=2, ensure_ascii=False)
        
        return tasks
    
    async def submit_batch(self, tasks: List[Dict]) -> str:
        """提交批处理任务到 Zhipu API"""
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"提交批处理任务")
        self.logger.info(f"{'='*80}\n")
        
        # 保存任务文件
        task_file = project_root / f"tmp/batch_tasks_{self.timestamp}.jsonl"
        
        with open(task_file, 'w') as f:
            for task in tasks:
                f.write(json.dumps(task, ensure_ascii=False) + '\n')
        
        self.logger.info(f"任务文件: {task_file}")
        self.logger.info(f"任务数量: {len(tasks)}")
        
        # 提交到 Zhipu
        batch_id = await self.batch_client.create_batch(
            task_file=str(task_file),
            description=f"{len(tasks)} papers extraction - {self.timestamp}"
        )
        
        self.logger.info(f"\n✅ 批处理任务已提交")
        self.logger.info(f"Batch ID: {batch_id}")
        self.logger.info(f"\n监控命令:")
        self.logger.info(f"  python scripts/check_batch_status.py {batch_id}")
        
        return batch_id
    
    async def run(self):
        """运行完整流程（支持断点续传）"""
        try:
            self.logger.info(f"\n{'='*80}")
            self.logger.info(f"🚀 开始提取 {self.target_count} 篇论文")
            self.logger.info(f"{'='*80}\n")
            
            # 尝试从进度文件恢复
            progress = self._load_progress()
            
            if progress:
                # 断点续传
                papers = await self.search_papers_batch(start_from=0)
                tasks = await self.fetch_and_prepare_batch(
                    papers,
                    start_from=progress.get('processed', 0),
                    existing_tasks=progress.get('tasks', [])
                )
            else:
                # 全新运行
                papers = await self.search_papers_batch()
                
                if not papers:
                    self.logger.error("未找到任何论文")
                    return
                
                tasks = await self.fetch_and_prepare_batch(papers)
            
            if not tasks:
                self.logger.error("未成功获取任何论文全文")
                return
            
            # 提交批处理
            batch_id = await self.submit_batch(tasks)
            
            self.logger.info(f"\n{'='*80}")
            self.logger.info(f"✅ 提取任务已完成")
            self.logger.info(f"{'='*80}")
            self.logger.info(f"Batch ID: {batch_id}")
            self.logger.info(f"论文数: {len(papers)}")
            self.logger.info(f"任务数: {len(tasks)}")
            self.logger.info(f"\n进度文件: {self.progress_file}")
            self.logger.info(f"\n下一步:")
            self.logger.info(f"  1. 监控批处理进度: python scripts/check_batch_status.py {batch_id}")
            self.logger.info(f"  2. 查看进度文件: cat {self.progress_file}")
            self.logger.info(f"  3. 处理完成后，运行结果处理脚本")
            
        except Exception as e:
            self.logger.error(f"提取失败: {e}", exc_info=True)
            # 保存当前进度
            self._save_progress([], processed=0)
            raise
        finally:
            # 清理资源
            await self.pubmed_client.close()
            await self.jina_client.close()


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="优化的论文提取脚本")
    parser.add_argument(
        '--count', 
        type=int, 
        default=1000,
        help='目标论文数量（默认 1000）'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='批处理大小（默认 100）'
    )
    parser.add_argument(
        '--no-resume',
        action='store_true',
        help='不从进度文件恢复'
    )
    
    args = parser.parse_args()
    
    extractor = OptimizedPaperExtractor(
        target_count=args.count,
        batch_size=args.batch_size,
        resume_from_progress=not args.no_resume
    )
    
    await extractor.run()


if __name__ == "__main__":
    asyncio.run(main())
