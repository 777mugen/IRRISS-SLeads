"""
CSV exporter for leads.
CSV 导出器。
"""

import csv
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any


class CSVExporter:
    """CSV 导出器"""
    
    # 重构后的字段列表
    PAPER_COLUMNS = [
        "DOI",               # DOI 标识符
        "标题",              # 文章标题
        "发表时间",          # YYYY-MM-DD
        "原文链接",          # https://doi.org/[DOI]
        "来源",              # 固定"PubMed"
        "通讯作者",          # 通讯作者姓名
        "单位地址",          # 通讯作者单位地址
        "联系电话",          # 通讯作者电话
        "电子邮箱",          # 通讯作者邮箱
        "其他作者信息",      # 一人一行展开
        "线索等级"           # A/B/C/D（只暴露等级，不暴露分数）
    ]
    
    TENDER_COLUMNS = [
        "公告编号",
        "项目名称",
        "招标单位",
        "联系人姓名",
        "联系邮箱",
        "联系电话",
        "地址",
        "预算信息",
        "发生时间",
        "等级",
        "分数",
        "命中关键词",
        "来源链接",
        "变更标记"
    ]
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_paper_leads(
        self, 
        leads: list[dict[str, Any]], 
        filename: str | None = None,
        include_diff: bool = False
    ) -> str:
        """
        导出论文线索
        
        Args:
            leads: 线索列表
            filename: 文件名（不含路径）
            include_diff: 是否包含变更标记
            
        Returns:
            导出文件路径
        """
        if filename is None:
            today = date.today()
            suffix = "full" if include_diff else "incremental"
            filename = f"paper_leads_{suffix}_{today}.csv"
        
        filepath = self.output_dir / "paper_leads" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(self.PAPER_COLUMNS)
            
            for lead in leads:
                row = [
                    lead.get('doi', ''),
                    lead.get('title', ''),
                    self._format_date(lead.get('published_at')),
                    lead.get('article_url', ''),
                    lead.get('source', 'PubMed'),
                    lead.get('name', ''),
                    lead.get('address', ''),  # 单位地址
                    lead.get('phone', ''),
                    lead.get('email', ''),
                    self._format_all_authors_expanded(lead.get('all_authors')),
                    lead.get('grade', '')
                ]
                writer.writerow(row)
        
        return str(filepath)
    
    def export_tender_leads(
        self, 
        leads: list[dict[str, Any]], 
        filename: str | None = None,
        include_diff: bool = False
    ) -> str:
        """
        导出招标线索
        
        Args:
            leads: 线索列表
            filename: 文件名（不含路径）
            include_diff: 是否包含变更标记
            
        Returns:
            导出文件路径
        """
        if filename is None:
            today = date.today()
            suffix = "full" if include_diff else "incremental"
            filename = f"tender_leads_{suffix}_{today}.csv"
        
        filepath = self.output_dir / "tender_leads" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(self.TENDER_COLUMNS)
            
            for lead in leads:
                row = [
                    lead.get('announcement_id', ''),
                    lead.get('project_name', ''),
                    lead.get('organization', ''),
                    lead.get('name', ''),
                    lead.get('email', ''),
                    lead.get('phone', ''),
                    lead.get('address', ''),
                    lead.get('budget_info', ''),
                    self._format_date(lead.get('published_at')),
                    lead.get('grade', ''),
                    lead.get('score', ''),
                    self._format_keywords(lead.get('keywords_matched')),
                    lead.get('source_url', ''),
                    lead.get('change_marker', '') if include_diff else ''
                ]
                writer.writerow(row)
        
        return str(filepath)
    
    def _format_date(self, date_value: date | str | None) -> str:
        """格式化日期"""
        if date_value is None:
            return ''
        if isinstance(date_value, str):
            return date_value
        return date_value.strftime('%Y-%m-%d')
    
    def _format_keywords(self, keywords: list[str] | None) -> str:
        """格式化关键词列表"""
        if not keywords:
            return ''
        return ','.join(keywords)
    
    def _format_all_authors(self, authors: Any) -> str:
        """格式化全部作者信息（JSON 格式）"""
        if not authors:
            return ''
        if isinstance(authors, str):
            return authors
        return json.dumps(authors, ensure_ascii=False)
    
    def _format_all_authors_expanded(self, authors: Any) -> str:
        """
        格式化全部作者信息（一人一行展开）
        
        数据库存储（JSON）:
        [
            {"name": "张三", "institution": "清华大学", "email": "abc@tsinghua.edu.cn", "phone": "+86-138-0000-0000"}
        ]
        
        CSV 导出（一人一行）:
        张三, 清华大学, abc@tsinghua.edu.cn, +86-138-0000-0000
        李四, 北京大学, def@pku.edu.cn, 
        """
        if not authors:
            return ''
        
        # 如果是字符串，先解析为 JSON
        if isinstance(authors, str):
            try:
                authors = json.loads(authors)
            except:
                return authors
        
        # 展开为一人一行
        lines = []
        for author in authors:
            if isinstance(author, dict):
                parts = [
                    author.get('name', ''),
                    author.get('institution', ''),
                    author.get('email', ''),
                    author.get('phone', '')
                ]
                lines.append(', '.join(part for part in parts if part))
        
        return '\n'.join(lines)
