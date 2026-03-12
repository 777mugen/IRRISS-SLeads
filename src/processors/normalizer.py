"""
Processor for data deduplication and normalization.
数据去重和标准化处理器。
"""

from datetime import datetime
from typing import Any


def normalize_lead(lead: dict[str, Any], lead_type: str) -> dict[str, Any]:
    """
    标准化线索数据
    
    Args:
        lead: 原始线索数据
        lead_type: 'paper' 或 'tender'
        
    Returns:
        标准化后的数据
    """
    normalized = lead.copy()
    
    # 清理字符串字段
    string_fields = ['name', 'email', 'phone', 'address', 'institution', 'organization']
    for field in string_fields:
        if field in normalized and normalized[field]:
            normalized[field] = str(normalized[field]).strip()
    
    # 标准化邮箱（小写）
    if 'email' in normalized and normalized['email']:
        normalized['email'] = normalized['email'].lower()
    
    # 标准化手机号（去除空格和横线）
    if 'phone' in normalized and normalized['phone']:
        normalized['phone'] = str(normalized['phone']).replace(' ', '').replace('-', '')
    
    # 处理日期
    if 'published_at' in normalized and isinstance(normalized['published_at'], str):
        try:
            normalized['published_at'] = datetime.strptime(
                normalized['published_at'], '%Y-%m-%d'
            ).date()
        except ValueError:
            normalized['published_at'] = None
    
    # 确保 keywords_matched 是列表
    if 'keywords_matched' in normalized and not isinstance(normalized['keywords_matched'], list):
        if normalized['keywords_matched']:
            normalized['keywords_matched'] = [normalized['keywords_matched']]
        else:
            normalized['keywords_matched'] = []
    
    # 添加处理时间
    normalized['processed_at'] = datetime.utcnow()
    
    return normalized


def deduplicate_key(lead: dict[str, Any], lead_type: str) -> str:
    """
    生成去重键
    
    使用 [姓名 + 单位 / 联系方式 / 地址] 组合作为去重标识
    
    Args:
        lead: 线索数据
        lead_type: 'paper' 或 'tender'
        
    Returns:
        去重键字符串
    """
    if lead_type == 'paper':
        parts = [
            lead.get('name', ''),
            lead.get('institution', ''),
            lead.get('email', ''),
            lead.get('phone', ''),
            lead.get('address', ''),
        ]
    else:
        parts = [
            lead.get('name', ''),
            lead.get('organization', ''),
            lead.get('email', ''),
            lead.get('phone', ''),
            lead.get('address', ''),
        ]
    
    # 过滤空值并连接
    key_parts = [str(p).strip().lower() for p in parts if p]
    return '|'.join(key_parts)
