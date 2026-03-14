"""
内容截断器
用于提取论文的元数据部分，去除学术内容，避免模型注意力问题
"""

import re
from typing import List, Optional

from src.logging_config import get_logger


class ContentTruncator:
    """
    内容截断器
    
    原则：避免无效信息导致模型注意力问题
    """
    
    # 学术内容开始的关键词
    STOP_KEYWORDS = [
        # 标准章节标题
        'Introduction',
        'Methods',
        'Methodology',
        'Background',
        'Results',
        'Discussion',
        'Conclusion',
        'Conclusions',
        # 特殊章节
        'Abstract',
        'Keywords',
        'Abbreviations',
        'Acknowledgements',
        'Acknowledgments',
        'References',
        'Supplementary',
        'Plain Language Summary',  # CMJ 特殊格式
    ]
    
    def __init__(self):
        self.logger = get_logger()
    
    def extract_metadata_section(self, content: str) -> str:
        """
        提取论文元数据部分
        
        Args:
            content: 原始 Markdown 内容
            
        Returns:
            元数据部分（去除了学术内容）
        """
        if not content:
            return content
        
        # 1. 按段落分割
        paragraphs = content.split('\n\n')
        
        # 2. 找到学术内容开始的位置
        metadata_paragraphs = []
        
        for i, p in enumerate(paragraphs):
            # 跳过空段落
            if not p.strip():
                continue
            
            # 检查是否到达学术内容部分
            if self._is_section_start(p, paragraphs, i):
                self.logger.info(f"在第 {i} 个段落检测到学术内容开始: {p[:50]}...")
                break
            
            metadata_paragraphs.append(p)
        
        # 3. 合并元数据部分
        result = '\n\n'.join(metadata_paragraphs)
        
        # 4. 记录日志
        original_length = len(content)
        result_length = len(result)
        reduction = 100 * (1 - result_length / original_length) if original_length > 0 else 0
        
        self.logger.info(
            f"内容截断完成: 原始 {original_length} 字符 → "
            f"截断后 {result_length} 字符 (减少 {reduction:.1f}%)"
        )
        
        return result
    
    def _is_section_start(self, paragraph: str, paragraphs: List[str], index: int) -> bool:
        """
        判断段落是否是学术内容的开始
        
        Args:
            paragraph: 段落文本
            paragraphs: 所有段落列表
            index: 当前段落索引
            
        Returns:
            是否是学术内容开始
        """
        # 清理段落（去除前后空格）
        p = paragraph.strip()
        
        # 检查标题格式
        for keyword in self.STOP_KEYWORDS:
            # 匹配 1：Markdown 标题格式（# Introduction, ## Introduction）
            if re.match(rf'^#+\s+{keyword}\s*$', p, re.IGNORECASE):
                return True
            
            # 匹配 2：独立一行或后面跟其他文本（Abstract Plain Language Summary）
            if re.match(rf'^{keyword}(\s|$)', p, re.IGNORECASE):
                # 排除误匹配（例如 "Introduction to ..." 不是章节标题）
                # 只有当整行长度较短时才认为是标题
                if len(p.split()[0]) == len(keyword):  # 确保第一个词就是关键词
                    return True
            
            # 匹配 3：关键词 + Other Section（AME 出版社格式）
            # 例如："Introduction Other Section"
            if re.search(rf'{keyword}\s+Other\s+Section', p, re.IGNORECASE):
                return True
            
            # 匹配 4：下划线风格标题（Introduction 后面跟 -----）
            # 例如：
            # Introduction
            # ------------
            if index + 1 < len(paragraphs):
                next_p = paragraphs[index + 1].strip()
                # 检查当前段落是否匹配关键词
                if re.match(rf'^{keyword}\s*$', p, re.IGNORECASE):
                    # 检查下一个段落是否是下划线
                    if re.match(r'^[-]+$', next_p) or re.match(r'^[=]+$', next_p):
                        return True
        
        return False
    
    def extract_by_regex(self, content: str) -> dict:
        """
        使用正则提取元数据（备用方案）
        
        Args:
            content: 原始 Markdown 内容
            
        Returns:
            提取的元数据
        """
        result = {
            'title': None,
            'authors': [],
            'emails': [],
            'affiliations': []
        }
        
        # 提取标题（第一个大标题）
        title_match = re.search(r'^#+ (.+)$', content, re.MULTILINE)
        if title_match:
            result['title'] = title_match.group(1)
        
        # 提取作者列表（包含数字和符号的行）
        # 示例：Weiping Yang 1,#, Wei Xiao 2,#, Tao Li 3,4,*
        author_pattern = r'([A-Z][a-z]+ [A-Z][a-z]+ [\d,#\*]+)'
        result['authors'] = re.findall(author_pattern, content)
        
        # 提取邮箱
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        result['emails'] = re.findall(email_pattern, content)
        
        # 提取机构（包含 Department, University, Institute 的段落）
        affiliation_pattern = r'(\d+\. .*(?:Department|University|Institute).*)'
        result['affiliations'] = re.findall(affiliation_pattern, content)
        
        return result


def truncate_content(content: str) -> str:
    """
    便捷函数：截断内容
    
    Args:
        content: 原始内容
        
    Returns:
        截断后的内容
    """
    truncator = ContentTruncator()
    return truncator.extract_metadata_section(content)
