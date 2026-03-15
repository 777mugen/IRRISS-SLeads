"""
提取 1000 篇论文（PubMed API + Jina Reader + Zhipu 批处理）

流程：
1. 使用 PubMed Entrez API 搜索关键词
2. 获取 PMID 列表和论文基本信息
3. 使用 Jina Reader 获取论文全文 Markdown
4. 提交到 Zhipu 批处理 API 提取作者信息
5. 保存结果到数据库
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime, date
from typing import List, Dict

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.crawlers.pubmed_entrez import PubMedEntrezClient
from src.crawlers.jina_client import JinaClient
from src.llm.batch_client import ZhiPuBatchClient
from src.prompts.batch_extraction import BATCH_EXTRACTION_PROMPT_V2
from src.logging_config import get_logger
import yaml


class PaperExtractor1000:
    """1000 篇论文提取器"""
    
    def __init__(self, target_count: int = 1000):
        self.target_count = target_count
        self.logger = get_logger()
        
        # 加载关键词配置
        with open(project_root / "config/keywords.yaml") as f:
            self.keywords_config = yaml.safe_load(f)
        
        # 初始化客户端
        self.pubmed_client = PubMedEntrezClient()
        self.jina_client = JinaClient()
        self.batch_client = ZhiPuBatchClient()
    
    async def build_search_queries(self) -> List[str]:
        """
        构建搜索查询
        
        策略：组合核心关键词和设备关键词
        """
        queries = []
        
        # 英文核心关键词
        english_core = self.keywords_config['english']['core']
        english_equipment = self.keywords_config['english']['equipment']
        
        # 策略 1: 每个核心关键词单独搜索
        for keyword in english_core[:10]:  # 前 10 个核心关键词
            queries.append(f'"{keyword}"')
        
        # 策略 2: 核心关键词 + 设备关键词组合
        for core_kw in english_core[:5]:  # 前 5 个核心关键词
            for equip_kw in english_equipment[:3]:  # 前 3 个设备关键词
                queries.append(f'"{core_kw}" AND "{equip_kw}"')
        
        # 策略 3: 布尔组合（OR）
        # "Multiplex Immunofluorescence" OR "mIF" OR "TSA"
        queries.append(
            '"Multiplex Immunofluorescence" OR "mIF" OR "TSA"'
        )
        queries.append(
            '"Spatial Proteomics" OR "Spatial Transcriptomics"'
        )
        queries.append(
            '"Confocal Microscopy" OR "Fluorescence Microscopy"'
        )
        
        self.logger.info(f"构建了 {len(queries)} 个搜索查询")
        return queries
    
    async def search_papers(self) -> List[Dict]:
        """
        搜索论文，返回 PMID 和 DOI 列表
        
        目标：收集 1000 篇论文
        """
        queries = await self.build_search_queries()
        
        all_papers = []
        seen_pmids = set()
        
        # 每个查询的目标数量（平均分配）
        per_query = self.target_count // len(queries) + 50  # 多取一些，去重后刚好
        
        for i, query in enumerate(queries, 1):
            self.logger.info(f"\n[{i}/{len(queries)}] 执行查询: {query[:60]}...")
            
            # 搜索 2024-2026 年的论文（最新研究）
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
            
            # 避免 API 限流
            await asyncio.sleep(0.5)
        
        # 截断到目标数量
        all_papers = all_papers[:self.target_count]
        
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"搜索完成: {len(all_papers)} 篇论文")
        self.logger.info(f"{'='*80}\n")
        
        return all_papers
    
    async def fetch_and_prepare_batch(self, papers: List[Dict]) -> List[Dict]:
        """
        获取论文全文并准备批处理任务
        
        Args:
            papers: 论文列表 [{pmid, doi, title, ...}, ...]
            
        Returns:
            批处理任务列表
        """
        tasks = []
        stats = {
            'total': len(papers),
            'success': 0,
            'failed': 0,
            'no_doi': 0,
            'errors': []
        }
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_id = f"batch_1000papers_{timestamp}"
        
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"开始获取论文全文")
        self.logger.info(f"{'='*80}\n")
        
        for i, paper in enumerate(papers, 1):
            pmid = paper.get('pmid')
            doi = paper.get('doi')
            title = paper.get('title', 'N/A')[:50]
            
            self.logger.info(f"[{i}/{len(papers)}] PMID: {pmid} - {title}")
            
            if not doi:
                self.logger.warning(f"  ⚠️  无 DOI，跳过")
                stats['no_doi'] += 1
                continue
            
            try:
                # 使用 Jina Reader 获取论文全文
                content = await self.jina_client.read_paper(f"https://doi.org/{doi}")
                
                if not content or len(content) < 100:
                    self.logger.error(f"  ❌ 内容过短或为空")
                    stats['failed'] += 1
                    stats['errors'].append({
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
                stats['success'] += 1
                
            except Exception as e:
                self.logger.error(f"  ❌ 失败: {e}")
                stats['failed'] += 1
                stats['errors'].append({
                    'pmid': pmid,
                    'doi': doi,
                    'error': str(e)
                })
            
            # 每 10 篇保存一次进度
            if i % 10 == 0:
                progress_file = project_root / f"tmp/extraction_progress_{timestamp}.json"
                progress_file.parent.mkdir(exist_ok=True)
                with open(progress_file, 'w') as f:
                    json.dump({
                        'batch_id': batch_id,
                        'timestamp': timestamp,
                        'processed': i,
                        'total': len(papers),
                        'tasks_prepared': len(tasks),
                        'stats': stats
                    }, f, indent=2, ensure_ascii=False)
            
            # 避免 API 限流
            await asyncio.sleep(1.0)
        
        # 最终统计
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"全文获取完成")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"总论文数: {stats['total']}")
        self.logger.info(f"成功获取: {stats['success']}")
        self.logger.info(f"失败: {stats['failed']}")
        self.logger.info(f"无 DOI: {stats['no_doi']}")
        self.logger.info(f"批处理任务: {len(tasks)}")
        
        # 保存统计
        stats_file = project_root / f"tmp/extraction_stats_{timestamp}.json"
        with open(stats_file, 'w') as f:
            json.dump({
                'batch_id': batch_id,
                'timestamp': timestamp,
                'stats': stats,
                'task_count': len(tasks)
            }, f, indent=2, ensure_ascii=False)
        
        return tasks
    
    async def submit_batch(self, tasks: List[Dict]) -> str:
        """
        提交批处理任务到 Zhipu API
        
        Returns:
            批处理任务 ID
        """
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"提交批处理任务")
        self.logger.info(f"{'='*80}\n")
        
        # 保存任务文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        task_file = project_root / f"tmp/batch_tasks_{timestamp}.jsonl"
        task_file.parent.mkdir(exist_ok=True)
        
        with open(task_file, 'w') as f:
            for task in tasks:
                f.write(json.dumps(task, ensure_ascii=False) + '\n')
        
        self.logger.info(f"任务文件: {task_file}")
        self.logger.info(f"任务数量: {len(tasks)}")
        
        # 提交到 Zhipu
        batch_id = await self.batch_client.create_batch(
            task_file=str(task_file),
            description=f"1000 papers extraction - {timestamp}"
        )
        
        self.logger.info(f"\n✅ 批处理任务已提交")
        self.logger.info(f"Batch ID: {batch_id}")
        self.logger.info(f"\n监控命令:")
        self.logger.info(f"  python scripts/check_batch_status.py {batch_id}")
        
        return batch_id
    
    async def run(self):
        """运行完整流程"""
        try:
            self.logger.info(f"\n{'='*80}")
            self.logger.info(f"🚀 开始提取 {self.target_count} 篇论文")
            self.logger.info(f"{'='*80}\n")
            
            # Step 1: 搜索论文
            papers = await self.search_papers()
            
            if not papers:
                self.logger.error("未找到任何论文")
                return
            
            # Step 2: 获取全文并准备批处理任务
            tasks = await self.fetch_and_prepare_batch(papers)
            
            if not tasks:
                self.logger.error("未成功获取任何论文全文")
                return
            
            # Step 3: 提交批处理
            batch_id = await self.submit_batch(tasks)
            
            self.logger.info(f"\n{'='*80}")
            self.logger.info(f"✅ 提取任务已启动")
            self.logger.info(f"{'='*80}")
            self.logger.info(f"Batch ID: {batch_id}")
            self.logger.info(f"论文数: {len(papers)}")
            self.logger.info(f"任务数: {len(tasks)}")
            self.logger.info(f"\n下一步:")
            self.logger.info(f"  1. 监控批处理进度: python scripts/check_batch_status.py {batch_id}")
            self.logger.info(f"  2. 查看进度文件: tmp/extraction_progress_*.json")
            self.logger.info(f"  3. 处理完成后，运行结果处理脚本")
            
        except Exception as e:
            self.logger.error(f"提取失败: {e}", exc_info=True)
            raise
        finally:
            # 清理资源
            await self.pubmed_client.close()
            await self.jina_client.close()


async def main():
    """主函数"""
    extractor = PaperExtractor1000(target_count=1000)
    await extractor.run()


if __name__ == "__main__":
    asyncio.run(main())
