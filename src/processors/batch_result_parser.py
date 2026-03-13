"""
Batch Result Parser
批量结果解析器

负责解析智谱批量 API 返回的 JSONL 结果文件
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.logging_config import get_logger


class BatchResultParser:
    """
    批量结果解析器
    
    负责解析智谱批量 API 返回的 JSONL 结果文件
    """
    
    def __init__(self):
        self.logger = get_logger()
    
    def parse_result_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        解析结果文件
        
        Args:
            file_path: 结果文件路径
            
        Returns:
            解析后的结果列表
            [
                {
                    'custom_id': 'doi_10.1016_j.modpat.2023.100197',
                    'doi': '10.1016/j.modpat.2023.100197',
                    'status': 'success',
                    'data': {...},
                    'error': None
                },
                ...
            ]
        """
        if not file_path.exists():
            raise FileNotFoundError(f"结果文件不存在: {file_path}")
        
        results = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    result = json.loads(line)
                    parsed = self._parse_single_result(result)
                    results.append(parsed)
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"第 {line_num} 行 JSON 解析失败: {e}")
                    results.append({
                        'custom_id': None,
                        'doi': None,
                        'status': 'error',
                        'data': None,
                        'error': f'JSON 解析失败: {e}'
                    })
        
        self.logger.info(f"解析完成: {len(results)} 条结果")
        return results
    
    def _parse_single_result(self, result: Dict) -> Dict[str, Any]:
        """
        解析单个结果
        
        Args:
            result: 单个结果对象
            
        Returns:
            解析后的结果
        """
        custom_id = result.get('custom_id')
        
        # 从 custom_id 提取 DOI
        doi = None
        if custom_id and custom_id.startswith('doi_'):
            doi = custom_id[4:].replace('_', '/')
        
        response = result.get('response', {})
        status_code = response.get('status_code')
        
        if status_code == 200:
            # 成功
            body = response.get('body', {})
            content = body.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            # 尝试解析 JSON
            try:
                data = self._parse_llm_response(content)
                return {
                    'custom_id': custom_id,
                    'doi': doi,
                    'status': 'success',
                    'data': data,
                    'error': None
                }
            except Exception as e:
                return {
                    'custom_id': custom_id,
                    'doi': doi,
                    'status': 'parse_error',
                    'data': None,
                    'error': f'LLM 响应解析失败: {e}'
                }
        else:
            # 失败
            error_msg = response.get('body', {}).get('error', {}).get('message', 'Unknown error')
            return {
                'custom_id': custom_id,
                'doi': doi,
                'status': 'failed',
                'data': None,
                'error': f'API 错误 ({status_code}): {error_msg}'
            }
    
    def _parse_llm_response(self, content: str) -> Dict[str, Any]:
        """
        解析 LLM 返回的 JSON 内容
        
        Args:
            content: LLM 返回的文本
            
        Returns:
            解析后的结构化数据
            
        Raises:
            ValueError: 内容过长
            ValueError: JSON 解析失败
        """
        # 1. 内容长度限制（防止内存溢出）
        MAX_CONTENT_LENGTH = 100000  # 100KB
        if len(content) > MAX_CONTENT_LENGTH:
            raise ValueError(f"LLM 响应内容过长: {len(content)} 字节 (最大 {MAX_CONTENT_LENGTH})")
        
        # 2. 空内容检查
        if not content or not content.strip():
            raise ValueError("LLM 响应内容为空")
        
        # 3. 尝试直接解析 JSON
        try:
            data = json.loads(content)
            return self._validate_and_clean_data(data)
        except json.JSONDecodeError as e:
            self.logger.debug(f"直接 JSON 解析失败: {e}")
        
        # 4. 尝试提取 JSON 块
        import re
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return self._validate_and_clean_data(data)
            except json.JSONDecodeError as e:
                self.logger.debug(f"JSON 块提取解析失败: {e}")
        
        # 5. 所有尝试都失败
        raise ValueError(f"无法解析 LLM 响应为 JSON (内容长度: {len(content)}, 前 200 字符: {content[:200]}...)")
    
    def _validate_and_clean_data(self, data: Dict) -> Dict[str, Any]:
        """
        验证并清理提取的数据
        
        Args:
            data: 提取的数据
            
        Returns:
            清理后的数据
        """
        # 确保必要字段存在
        cleaned = {
            'title': data.get('title'),
            'published_at': self._parse_date(data.get('published_at')),
            'corresponding_author': {
                'name': None,
                'email': None,
                'phone': None,
                'institution': None,
                'address': None
            },
            'all_authors_info': data.get('all_authors_info'),
            'all_authors_info_cn': data.get('all_authors_info_cn')
        }
        
        # 提取通讯作者信息
        corr_author = data.get('corresponding_author', {})
        if isinstance(corr_author, dict):
            cleaned['corresponding_author'] = {
                'name': corr_author.get('name'),
                'email': corr_author.get('email'),
                'phone': corr_author.get('phone'),
                'institution': corr_author.get('institution'),
                'address': corr_author.get('address')
            }
        
        return cleaned
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[str]:
        """
        解析日期字符串
        
        Args:
            date_str: 日期字符串（YYYY-MM-DD 或其他格式）
            
        Returns:
            YYYY-MM-DD 格式的日期字符串，或 None
        """
        if not date_str:
            return None
        
        # 尝试多种日期格式
        date_formats = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%d/%m/%Y',
            '%B %d, %Y',
            '%b %d, %Y',
        ]
        
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # 如果都失败，返回 None
        self.logger.warning(f"无法解析日期: {date_str}")
        return None
    
    def get_summary(self, results: List[Dict]) -> Dict[str, int]:
        """
        获取结果摘要
        
        Args:
            results: 解析后的结果列表
            
        Returns:
            {
                'total': int,
                'success': int,
                'failed': int,
                'parse_error': int
            }
        """
        summary = {
            'total': len(results),
            'success': 0,
            'failed': 0,
            'parse_error': 0
        }
        
        for result in results:
            status = result.get('status')
            if status == 'success':
                summary['success'] += 1
            elif status == 'parse_error':
                summary['parse_error'] += 1
            else:
                summary['failed'] += 1
        
        return summary
