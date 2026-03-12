"""
Fallback extractor using regex patterns.
基于正则表达式的后备提取器（不依赖 LLM）。
"""

import re
from datetime import datetime
from typing import Any, Optional


class RegexPaperExtractor:
    """基于正则的论文提取器"""
    
    # 常见邮箱模式
    EMAIL_PATTERN = r'[\w\.-]+@[\w\.-]+\.\w+'
    
    # 日期模式
    DATE_PATTERNS = [
        r'(\d{4}-\d{2}-\d{2})',  # 2024-01-15
        r'(\d{4}/\d{2}/\d{2})',  # 2024/01/15
        r'(\w+ \d{4})',  # January 2024
        r'(\d{4})',  # 2024
    ]
    
    def extract(self, content: str) -> dict[str, Any]:
        """
        从页面内容中提取论文信息
        
        Args:
            content: 页面 Markdown 内容
            
        Returns:
            提取的字段字典
        """
        result = {
            'title': self._extract_title(content),
            'name': self._extract_author(content),
            'institution': self._extract_institution(content),
            'address': self._extract_address(content),
            'email': self._extract_email(content),
            'published_at': self._extract_date(content),
            'keywords_matched': [],
        }
        
        # 检查必填字段
        missing = [k for k, v in result.items() if not v and k in ['title', 'name', 'institution', 'email']]
        if missing:
            result['_missing_fields'] = missing
        
        return result
    
    def _extract_title(self, content: str) -> Optional[str]:
        """提取标题"""
        # 查找 Title: 或 Markdown 标题
        patterns = [
            r'^Title:\s*(.+)$',
            r'^#\s+(.+)$',
            r'^##\s+(.+)$',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.MULTILINE)
            if match:
                title = match.group(1).strip()
                # 清理常见的后缀
                title = re.sub(r'\s*-\s*PubMed\s*$', '', title)
                return title
        
        # 如果没找到，取第一行非空内容
        lines = [l.strip() for l in content.split('\n') if l.strip()]
        if lines:
            # 跳过可能的元数据行
            for line in lines[:5]:
                if not line.startswith(('http', 'URL', 'Markdown', 'event:')):
                    return line[:200]  # 限制长度
        
        return None
    
    def _extract_author(self, content: str) -> Optional[str]:
        """提取作者姓名"""
        # 查找 Authors 或 Author 部分
        patterns = [
            r'(?:Authors?|Corresponding Author)[:\s]*\n?\s*([^\n]+)',
            r'^([A-Z][a-z]+ [A-Z][a-z]+)(?:,\s*[A-Z][a-z]+ [A-Z][a-z]+)*',  # Name, Name, Name
            r'([A-Z][a-z]+ [A-Z]\. [A-Z][a-z]+)',  # First M. Last
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.MULTILINE)
            if match:
                authors = match.group(1).strip()
                # 取第一个作者
                if ',' in authors:
                    authors = authors.split(',')[0].strip()
                elif ' and ' in authors.lower():
                    authors = authors.split()[0] + ' ' + authors.split()[1] if len(authors.split()) > 1 else authors
                return authors[:100]
        
        return None
    
    def _extract_institution(self, content: str) -> Optional[str]:
        """提取机构"""
        # 查找 Affiliation 或 Institution
        patterns = [
            r'(?:Affiliations?|Institution|Department)[:\s]*\n?\s*([^\n]+)',
            r'([A-Z][a-z]+ (?:University|Institute|Hospital|Center|College)[^,\n]*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                inst = match.group(1).strip()
                # 清理
                inst = re.sub(r'^[-\s]+', '', inst)
                return inst[:200]
        
        return None
    
    def _extract_address(self, content: str) -> Optional[str]:
        """提取地址"""
        # 查找 Address 或地址模式
        patterns = [
            r'(?:Address|Location)[:\s]*\n?\s*([^\n]+)',
            r'([A-Z][a-z]+(?: City)?,?\s*[A-Z][a-z]+,?\s*[A-Z]{2,}(?:\s+\d{5})?)',  # City, State Country
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                addr = match.group(1).strip()
                return addr[:200]
        
        # 尝试从机构中提取城市/国家
        inst_match = re.search(r',\s*([^,]+(?:City|Country|China|Israel|USA|Japan|Germany)[^,]*)\s*$', content[:2000])
        if inst_match:
            return inst_match.group(1).strip()
        
        return None
    
    def _extract_email(self, content: str) -> Optional[str]:
        """提取邮箱"""
        matches = re.findall(self.EMAIL_PATTERN, content)
        if matches:
            # 优先选择包含常见学术域名的
            for email in matches:
                if any(domain in email.lower() for domain in ['.edu', '.ac.', '.org']):
                    return email.lower()
            # 否则返回第一个
            return matches[0].lower()
        return None
    
    def _extract_date(self, content: str) -> Optional[str]:
        """提取发布日期"""
        for pattern in self.DATE_PATTERNS:
            match = re.search(pattern, content)
            if match:
                date_str = match.group(1)
                # 尝试标准化为 YYYY-MM-DD
                try:
                    if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
                        return date_str
                    elif re.match(r'\d{4}/\d{2}/\d{2}', date_str):
                        return date_str.replace('/', '-')
                    elif re.match(r'\d{4}$', date_str):
                        return f"{date_str}-01-01"  # 默认1月1日
                    else:
                        # 尝试解析月份名
                        dt = datetime.strptime(date_str, '%B %Y')
                        return dt.strftime('%Y-%m-01')
                except:
                    pass
        return None
    
    def validate_required_fields(self, data: dict[str, Any]) -> bool:
        """验证必填字段"""
        required = ["title", "name", "institution", "email"]
        return all(data.get(field) for field in required)
