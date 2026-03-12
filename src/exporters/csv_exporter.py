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
    
    PAPER_COLUMNS = [
        "PMID",              # 论文唯一标识
        "DOI",               # DOI 标识符
        "文章标题",
        "发表时间",
        "通讯作者姓名",
        "通讯作者单位",
        "通讯作者邮箱",
        "通讯作者电话",
        "通讯作者地址",
        "全部作者信息",      # JSON 格式的所有作者
        "等级",
        "分数",
        "命中关键词",
        "来源链接",          # 线索唯一标识 (URL)
        "变更标记"
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
                    lead.get('pmid', ''),
                    lead.get('doi', ''),
                    lead.get('title', ''),
                    self._format_date(lead.get('published_at')),
                    lead.get('name', ''),
                    lead.get('institution', ''),
                    lead.get('email', ''),
                    lead.get('phone', ''),
                    lead.get('address', ''),
                    self._format_all_authors(lead.get('all_authors')),
                    lead.get('grade', ''),
                    lead.get('score', ''),
                    self._format_keywords(lead.get('keywords_matched')),
                    lead.get('source_url', ''),
                    lead.get('change_marker', '') if include_diff else ''
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
        """格式化全部作者信息"""
        if not authors:
            return ''
        if isinstance(authors, str):
            return authors
        return json.dumps(authors, ensure_ascii=False)
