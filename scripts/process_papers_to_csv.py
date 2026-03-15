#!/usr/bin/env python3
"""
完整的新流程：从搜索结果处理论文并输出 CSV

输入：tmp/pubmed_search_*.json（搜索结果）
输出：CSV 文件（包含评级）
"""

import asyncio
import csv
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from src.db.models import RawMarkdown, PaperLead
from src.db.utils import get_session
from src.scoring.paper_scorer import PaperScorer
from src.logging_config import get_logger
from src.prompts.batch_extraction import BATCH_EXTRACTION_PROMPT_V1
import httpx


class ZhipuPipeline:
    """智谱完整流程"""
    
    def __init__(self):
        self.logger = get_logger()
        self.api_key = None  # 将在运行时从 config 加载
        self.base_url = "https://open.bigmodel.cn/api/paas/v4"
        self.scorer = PaperScorer()
        self._client = None
    
    async def init(self):
        """初始化"""
        from src.config import config
        self.api_key = config.zai_api_key
        self._client = httpx.AsyncClient(timeout=120.0)
    
    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
    
    async def read_url(self, url: str) -> str:
        """智谱网页阅读"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "url": url,
            "return_format": "markdown",
            "retain_images": False,
            "with_links_summary": False,
            "timeout": 30
        }
        
        try:
            response = await self._client.post(
                f"{self.base_url}/reader",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data.get('reader_result', {}).get('content', '')
        except Exception as e:
            self.logger.error(f"网页阅读失败 {url}: {e}")
            return ''
    
    async def extract_info(self, content: str) -> Dict:
        """智谱结构化输出"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        user_content = BATCH_EXTRACTION_PROMPT_V1.replace(
            "{markdown_content}",
            content
        )
        
        payload = {
            "model": "glm-4-plus",
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的学术论文信息提取助手。严格按照规则提取，返回 JSON 格式。"
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        
        try:
            response = await self._client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            
            content = data['choices'][0]['message']['content']
            return json.loads(content)
        except Exception as e:
            self.logger.error(f"信息提取失败: {e}")
            return {}
    
    async def process_paper(self, paper: Dict, index: int, total: int) -> Dict:
        """处理单篇论文"""
        doi = paper.get('doi')
        
        if not doi:
            self.logger.warning(f"[{index}/{total}] 跳过（无 DOI）")
            return None
        
        self.logger.info(f"[{index}/{total}] 处理: {doi}")
        
        try:
            # 步骤 1: 网页阅读
            url = f"https://doi.org/{doi}"
            content = await self.read_url(url)
            
            if not content:
                self.logger.error(f"[{index}/{total}] ❌ 网页阅读失败")
                return None
            
            self.logger.info(f"[{index}/{total}] ✅ 网页阅读成功（{len(content)} 字符）")
            
            # 步骤 2: 结构化输出
            extracted = await self.extract_info(content)
            
            if not extracted:
                self.logger.error(f"[{index}/{total}] ❌ 信息提取失败")
                return None
            
            self.logger.info(f"[{index}/{total}] ✅ 信息提取成功")
            
            # 步骤 3: 评分
            lead_data = {
                'doi': doi,
                'title': paper.get('title'),
                'published_at': paper.get('published_date'),
                **extracted
            }
            
            score = self.scorer.score(lead_data)
            
            # 分级
            if score >= 80:
                grade = 'A'
            elif score >= 60:
                grade = 'B'
            elif score >= 40:
                grade = 'C'
            else:
                grade = 'D'
            
            self.logger.info(f"[{index}/{total}] ✅ 评分完成：{score} 分（{grade} 级）")
            
            return {
                **lead_data,
                'score': score,
                'grade': grade,
                'pipeline_source': 'pipeline_v2_zhipu_reader'
            }
        
        except Exception as e:
            self.logger.error(f"[{index}/{total}] ❌ 处理失败: {e}")
            return None
    
    def export_to_csv(self, results: List[Dict], output_file: Path):
        """导出到 CSV"""
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # 写入表头
            writer.writerow([
                'DOI', 'PMID', '标题', '发表日期', '评级', '分数',
                '通讯作者', '邮箱', '电话', '机构（中文）',
                'Pipeline 来源', '处理时间'
            ])
            
            # 写入数据
            for result in results:
                writer.writerow([
                    result.get('doi'),
                    result.get('pmid'),
                    result.get('title'),
                    result.get('published_at'),
                    result.get('grade'),
                    result.get('score'),
                    result.get('name'),
                    result.get('email'),
                    result.get('phone'),
                    result.get('institution_cn'),
                    result.get('pipeline_source'),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ])
        
        self.logger.info(f"✅ 已导出到: {output_file}")
        self.logger.info(f"   总计: {len(results)} 篇论文")


async def main():
    """主函数"""
    pipeline = ZhipuPipeline()
    await pipeline.init()
    
    try:
        # 读取搜索结果
        search_files = sorted(Path('tmp').glob('pubmed_search_*.json'))
        if not search_files:
            pipeline.logger.error("没有找到搜索结果文件")
            return
        
        latest = search_files[-1]
        pipeline.logger.info(f"📂 读取搜索结果: {latest}")
        
        with open(latest) as f:
            papers = json.load(f)
        
        pipeline.logger.info(f"📊 论文数量: {len(papers)}")
        
        # 处理论文
        results = []
        
        for i, paper in enumerate(papers, 1):
            result = await pipeline.process_paper(paper, i, len(papers))
            
            if result:
                results.append(result)
            
            # 每处理 10 篇保存一次进度
            if i % 10 == 0:
                output_file = Path(f"tmp/papers_progress_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
                pipeline.export_to_csv(results, output_file)
            
            # 避免请求过快
            await asyncio.sleep(2)
        
        # 最终输出
        output_file = Path(f"tmp/papers_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        pipeline.export_to_csv(results, output_file)
        
        # 统计
        pipeline.logger.info(f"\n{'='*80}")
        pipeline.logger.info(f"处理完成统计")
        pipeline.logger.info(f"{'='*80}")
        pipeline.logger.info(f"总论文数: {len(papers)}")
        pipeline.logger.info(f"成功处理: {len(results)}")
        pipeline.logger.info(f"成功率: {len(results)/len(papers)*100:.1f}%")
        
        # 分级统计
        grade_counts = {}
        for result in results:
            grade = result.get('grade', 'D')
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
        
        pipeline.logger.info(f"\n分级统计:")
        for grade in ['A', 'B', 'C', 'D']:
            count = grade_counts.get(grade, 0)
            pipeline.logger.info(f"  {grade} 级: {count} 篇 ({count/len(results)*100:.1f}%)")
    
    finally:
        await pipeline.close()


if __name__ == "__main__":
    asyncio.run(main())
