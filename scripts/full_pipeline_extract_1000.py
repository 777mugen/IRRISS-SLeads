#!/usr/bin/env python3
"""
完整的新流程：PubMed 搜索 → 智谱网页阅读 → 结构化输出 → 评级 → CSV

步骤：
1. 从 PubMed 搜索关键词，获取 1000 篇论文
2. 使用智谱网页阅读 API 获取内容
3. 使用智谱结构化输出 API 提取信息
4. 评分和分级（A/B/C/D）
5. 输出 CSV 文件
"""

import asyncio
import csv
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.crawlers.pubmed_entrez import PubMedEntrezClient
from src.db.models import PaperLead
from src.db.utils import get_session
from src.scoring.paper_scorer import PaperScorer
from src.logging_config import get_logger
import yaml


class FullPipelineExtractor:
    """完整流程提取器"""
    
    def __init__(self, target_count: int = 1000):
        self.target_count = target_count
        self.logger = get_logger()
        
        # 加载关键词
        with open(Path(__file__).parent.parent / "config/keywords.yaml") as f:
            self.keywords_config = yaml.safe_load(f)
        
        # 初始化客户端
        self.pubmed_client = PubMedEntrezClient()
        self.scorer = PaperScorer()
        
        # 统计
        self.stats = {
            'searched': 0,
            'fetched': 0,
            'extracted': 0,
            'failed': 0
        }
    
    async def search_pubmed(self) -> List[Dict]:
        """步骤 1: 搜索 PubMed 获取论文列表"""
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"步骤 1: 搜索 PubMed（目标: {self.target_count} 篇）")
        self.logger.info(f"{'='*80}")
        
        all_papers = []
        seen_dois = set()
        
        # 遍历所有关键词类别
        for category, keywords in self.keywords_config.items():
            if len(all_papers) >= self.target_count:
                break
            
            self.logger.info(f"\n分类: {category}")
            
            for keyword in keywords:
                if len(all_papers) >= self.target_count:
                    break
                
                try:
                    self.logger.info(f"  搜索: {keyword}")
                    
                    # 搜索 PubMed
                    pmids = await self.pubmed_client.search(
                        keyword,
                        max_results=min(100, self.target_count - len(all_papers))
                    )
                    
                    if not pmids:
                        continue
                    
                    # 获取详细信息
                    papers = await self.pubmed_client.fetch_details(pmids)
                    
                    # 去重
                    for paper in papers:
                        doi = paper.get('doi')
                        if doi and doi not in seen_dois:
                            all_papers.append(paper)
                            seen_dois.add(doi)
                    
                    self.logger.info(f"    找到: {len(pmids)} 篇，去重后: {len(all_papers)} 篇")
                    
                    # 避免请求过快
                    await asyncio.sleep(0.5)
                
                except Exception as e:
                    self.logger.error(f"    ❌ 搜索失败: {e}")
        
        self.stats['searched'] = len(all_papers)
        self.logger.info(f"\n✅ 搜索完成: {len(all_papers)} 篇论文")
        
        return all_papers
    
    async def process_papers(self, papers: List[Dict]) -> List[PaperLead]:
        """步骤 2-3: 网页阅读 + 结构化输出"""
        from scripts.extract_with_zhipu_reader import extract_papers_with_zhipu_reader
        
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"步骤 2-3: 智谱网页阅读 + 结构化输出")
        self.logger.info(f"{'='*80}")
        
        # 这里需要先保存到 raw_markdown 表
        # 然后调用 extract_with_zhipu_reader 处理
        
        leads = []
        
        # TODO: 实现完整流程
        # 1. 保存 DOI 到 raw_markdown（状态：pending）
        # 2. 调用智谱网页阅读 API 获取内容
        # 3. 调用智谱结构化输出 API 提取信息
        # 4. 保存到 paper_leads 表
        
        return leads
    
    def score_and_grade(self, leads: List[PaperLead]) -> List[PaperLead]:
        """步骤 4: 评分和分级"""
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"步骤 4: 评分和分级")
        self.logger.info(f"{'='*80}")
        
        for lead in leads:
            # 计算分数
            score = self.scorer.score(lead)
            lead.score = score
            
            # 分级
            if score >= 80:
                lead.grade = 'A'
            elif score >= 60:
                lead.grade = 'B'
            elif score >= 40:
                lead.grade = 'C'
            else:
                lead.grade = 'D'
        
        # 统计分级结果
        grade_counts = {}
        for lead in leads:
            grade = lead.grade or 'D'
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
        
        self.logger.info(f"分级统计:")
        for grade in ['A', 'B', 'C', 'D']:
            count = grade_counts.get(grade, 0)
            self.logger.info(f"  {grade} 级: {count} 篇 ({count/len(leads)*100:.1f}%)")
        
        return leads
    
    def export_to_csv(self, leads: List[PaperLead], output_file: Path):
        """步骤 5: 导出到 CSV"""
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"步骤 5: 导出 CSV")
        self.logger.info(f"{'='*80}")
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # 写入表头
            writer.writerow([
                'DOI', '标题', '发表日期', '评级', '分数',
                '通讯作者', '邮箱', '电话', '机构',
                'Pipeline 来源', '创建时间'
            ])
            
            # 写入数据
            for lead in leads:
                writer.writerow([
                    lead.doi,
                    lead.title,
                    lead.published_at,
                    lead.grade,
                    lead.score,
                    lead.name,
                    lead.email,
                    lead.phone,
                    lead.institution_cn,
                    lead.pipeline_source,
                    lead.created_at.strftime('%Y-%m-%d %H:%M:%S')
                ])
        
        self.logger.info(f"✅ 已导出到: {output_file}")
        self.logger.info(f"   总计: {len(leads)} 篇论文")


async def main():
    """主函数"""
    extractor = FullPipelineExtractor(target_count=1000)
    
    try:
        # 步骤 1: 搜索 PubMed
        papers = await extractor.search_pubmed()
        
        if not papers:
            extractor.logger.error("没有找到论文")
            return
        
        # 步骤 2-3: 处理论文（网页阅读 + 结构化输出）
        # leads = await extractor.process_papers(papers)
        
        # 步骤 4: 评分和分级
        # leads = extractor.score_and_grade(leads)
        
        # 步骤 5: 导出 CSV
        # output_file = Path(f"tmp/papers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        # extractor.export_to_csv(leads, output_file)
        
        # 临时：只执行步骤 1
        extractor.logger.info(f"\n{'='*80}")
        extractor.logger.info(f"临时输出：搜索结果")
        extractor.logger.info(f"{'='*80}")
        
        output_file = Path(f"tmp/pubmed_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        import json
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(papers, f, ensure_ascii=False, indent=2)
        
        extractor.logger.info(f"✅ 已保存搜索结果到: {output_file}")
        extractor.logger.info(f"   总计: {len(papers)} 篇论文")
        
    finally:
        await extractor.pubmed_client.close()


if __name__ == "__main__":
    asyncio.run(main())
