"""
失败分析系统
自动分析批处理失败论文的原因，提炼共性，并尝试解决
"""

import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import Counter

from sqlalchemy import select, and_
from src.db.models import RawMarkdown
from src.db.utils import get_session
from src.logging_config import get_logger


class FailureAnalyzer:
    """失败分析器"""
    
    def __init__(self):
        self.logger = get_logger()
    
    async def get_failed_papers(self, limit: int = 100) -> List[RawMarkdown]:
        """
        获取失败的论文
        
        Args:
            limit: 最多获取多少条
            
        Returns:
            失败的论文列表
        """
        async with get_session() as session:
            query = select(RawMarkdown).where(
                RawMarkdown.processing_status == 'failed'
            ).order_by(
                RawMarkdown.processed_at.desc()
            ).limit(limit)
            
            result = await session.execute(query)
            papers = result.scalars().all()
            
            return papers
    
    async def analyze_failures(self, papers: List[RawMarkdown]) -> Dict[str, Any]:
        """
        分析失败原因
        
        Args:
            papers: 失败的论文列表
            
        Returns:
            分析结果
        """
        if not papers:
            return {
                'total': 0,
                'categories': {},
                'patterns': {},
                'recommendations': []
            }
        
        # 分类失败原因
        error_categories = Counter()
        error_patterns = {}
        content_stats = {
            'lengths': [],
            'has_authors': 0,
            'has_email': 0,
            'has_doi': 0
        }
        
        for paper in papers:
            error_msg = paper.error_message or 'Unknown'
            
            # 1. 分类错误类型
            if 'Jina' in error_msg or 'timeout' in error_msg.lower():
                category = 'jina_api'
            elif 'parse' in error_msg.lower() or 'json' in error_msg.lower():
                category = 'parse_error'
            elif 'content_too_short' in error_msg.lower():
                category = 'content_short'
            elif 'validation' in error_msg.lower():
                category = 'validation_error'
            elif 'zhipu' in error_msg.lower() or 'batch' in error_msg.lower():
                category = 'zhipu_api'
            else:
                category = 'unknown'
            
            error_categories[category] += 1
            
            # 2. 记录错误详情
            if category not in error_patterns:
                error_patterns[category] = []
            
            error_patterns[category].append({
                'doi': paper.doi,
                'error': error_msg[:200],
                'retry_count': paper.retry_count,
                'content_length': len(paper.markdown_content) if paper.markdown_content else 0
            })
            
            # 3. 统计内容特征
            if paper.markdown_content:
                content_stats['lengths'].append(len(paper.markdown_content))
                
                # 检查是否包含关键信息
                if re.search(r'[A-Z][a-z]+\s+[A-Z][a-z]+', paper.markdown_content):
                    content_stats['has_authors'] += 1
                
                if re.search(r'[\w\.-]+@[\w\.-]+\.\w+', paper.markdown_content):
                    content_stats['has_email'] += 1
        
        # 4. 计算统计信息
        content_length_avg = (
            sum(content_stats['lengths']) / len(content_stats['lengths'])
            if content_stats['lengths'] else 0
        )
        
        # 5. 生成建议
        recommendations = self._generate_recommendations(
            error_categories,
            content_stats,
            content_length_avg
        )
        
        return {
            'total': len(papers),
            'categories': dict(error_categories),
            'patterns': error_patterns,
            'content_stats': {
                'avg_length': content_length_avg,
                'max_length': max(content_stats['lengths']) if content_stats['lengths'] else 0,
                'min_length': min(content_stats['lengths']) if content_stats['lengths'] else 0,
                'has_authors_count': content_stats['has_authors'],
                'has_email_count': content_stats['has_email'],
            },
            'recommendations': recommendations
        }
    
    def _generate_recommendations(
        self,
        error_categories: Counter,
        content_stats: Dict,
        avg_length: float
    ) -> List[str]:
        """生成改进建议"""
        
        recommendations = []
        
        # Jina API 失败
        if error_categories.get('jina_api', 0) > 5:
            recommendations.append(
                f"⚠️ Jina API 失败较多（{error_categories['jina_api']} 次）\n"
                "建议：\n"
                "  1. 增加 Jina API 超时时间（当前 95s → 120s）\n"
                "  2. 添加重试机制（当前已实现，max_retries=3）\n"
                "  3. 检查网络连接稳定性"
            )
        
        # 内容过短
        if error_categories.get('content_short', 0) > 3:
            recommendations.append(
                f"⚠️ 内容过短较多（{error_categories['content_short']} 次）\n"
                "可能原因：\n"
                "  1. 付费墙拦截\n"
                "  2. 反爬虫机制\n"
                "  3. DOI 不存在\n"
                "建议：标记为人工复核"
            )
        
        # 解析错误
        if error_categories.get('parse_error', 0) > 3:
            recommendations.append(
                f"⚠️ 解析错误较多（{error_categories['parse_error']} 次）\n"
                "建议：\n"
                "  1. 优化 Prompt 格式说明\n"
                "  2. 添加 JSON 格式验证\n"
                "  3. 增加容错处理"
            )
        
        # 内容长度分析
        if avg_length > 100000:
            recommendations.append(
                f"⚠️ 内容长度偏大（平均 {avg_length:.0f} 字符）\n"
                "可能影响：\n"
                "  1. Token 超限\n"
                "  2. 处理时间过长\n"
                "建议：考虑优化 Prompt 或分段处理"
            )
        
        # 缺少关键信息
        if content_stats['has_email_count'] < len(content_stats['lengths']) * 0.5:
            recommendations.append(
                f"⚠️ 邮箱提取率偏低（{content_stats['has_email_count']}/{len(content_stats['lengths'])}）\n"
                "可能原因：\n"
                "  1. 原文确实没有邮箱\n"
                "  2. 邮箱格式特殊（如：{at}符号）\n"
                "建议：检查 Jina Reader 保留规则"
            )
        
        if not recommendations:
            recommendations.append(
                "✅ 失败原因分散，暂无明显改进方向\n"
                "建议：继续监控，积累更多数据"
            )
        
        return recommendations
    
    async def check_retry_attempts(self) -> Dict[str, Any]:
        """
        检查重试尝试情况
        
        Returns:
            重试统计
        """
        async with get_session() as session:
            from sqlalchemy import func
            
            # 统计不同重试次数的论文数量
            query = select(
                RawMarkdown.retry_count,
                func.count(RawMarkdown.id)
            ).where(
                RawMarkdown.processing_status == 'failed'
            ).group_by(
                RawMarkdown.retry_count
            ).order_by(
                RawMarkdown.retry_count
            )
            
            result = await session.execute(query)
            retry_stats = dict(result.all())
            
            # 统计达到最大重试次数的论文
            max_retries = 3
            query2 = select(func.count(RawMarkdown.id)).where(
                and_(
                    RawMarkdown.processing_status == 'failed',
                    RawMarkdown.retry_count >= max_retries
                )
            )
            
            result2 = await session.execute(query2)
            max_retry_count = result2.scalar()
            
            return {
                'retry_distribution': retry_stats,
                'max_retry_count': max_retry_count,
                'needs_manual_review': max_retry_count > 0
            }
    
    async def generate_report(self) -> str:
        """
        生成失败分析报告
        
        Returns:
            Markdown 格式的报告
        """
        # 获取失败的论文
        papers = await self.get_failed_papers(limit=100)
        
        if not papers:
            return "✅ 没有失败的论文\n"
        
        # 分析失败原因
        analysis = await self.analyze_failures(papers)
        
        # 获取重试统计
        retry_stats = await self.check_retry_attempts()
        
        # 生成报告
        report_lines = [
            "# 批处理失败分析报告",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 📊 总体统计",
            "",
            f"- **失败论文总数**: {analysis['total']} 篇",
            f"- **已达最大重试次数**: {retry_stats['max_retry_count']} 篇",
            "",
            "## 📈 失败原因分类",
            ""
        ]
        
        # 添加分类统计
        for category, count in sorted(
            analysis['categories'].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            percentage = (count / analysis['total']) * 100
            report_lines.append(
                f"- **{category}**: {count} 篇 ({percentage:.1f}%)"
            )
        
        report_lines.extend([
            "",
            "## 📏 内容统计",
            "",
            f"- **平均长度**: {analysis['content_stats']['avg_length']:.0f} 字符",
            f"- **最大长度**: {analysis['content_stats']['max_length']} 字符",
            f"- **最小长度**: {analysis['content_stats']['min_length']} 字符",
            f"- **包含作者信息**: {analysis['content_stats']['has_authors_count']}/{analysis['total']} 篇",
            f"- **包含邮箱信息**: {analysis['content_stats']['has_email_count']}/{analysis['total']} 篇",
            "",
            "## 🔧 改进建议",
            ""
        ])
        
        # 添加建议
        for i, rec in enumerate(analysis['recommendations'], 1):
            report_lines.append(f"{i}. {rec}")
            report_lines.append("")
        
        # 添加重试分布
        if retry_stats['retry_distribution']:
            report_lines.extend([
                "## 🔄 重试统计",
                "",
                "| 重试次数 | 论文数量 |",
                "|---------|---------|"
            ])
            
            for retry_count, count in sorted(retry_stats['retry_distribution'].items()):
                report_lines.append(f"| {retry_count} | {count} |")
            
            report_lines.append("")
        
        # 添加需要人工复核的论文
        if retry_stats['needs_manual_review']:
            report_lines.extend([
                "## ⚠️ 需要人工复核",
                "",
                f"有 **{retry_stats['max_retry_count']}** 篇论文已达到最大重试次数（3次），建议人工复核。",
                ""
            ])
            
            # 列出前 10 篇
            max_retry_papers = [
                p for p in papers if p.retry_count >= 3
            ][:10]
            
            for i, paper in enumerate(max_retry_papers, 1):
                report_lines.append(
                    f"{i}. **{paper.doi}**"
                )
                report_lines.append(
                    f"   - 失败次数: {paper.retry_count}"
                )
                report_lines.append(
                    f"   - 错误: {paper.error_message[:100] if paper.error_message else 'N/A'}"
                )
                report_lines.append("")
        
        return "\n".join(report_lines)


async def main():
    """测试失败分析器"""
    analyzer = FailureAnalyzer()
    
    report = await analyzer.generate_report()
    print(report)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
