"""
Tender lead scorer.
招标线索评分引擎。
"""

from typing import Any

from src.config import config
from .base import BaseScorer, days_since


class TenderScorer(BaseScorer):
    """招标线索评分引擎"""
    
    def __init__(self):
        self.weights = config.scoring_tender.get('weights', {})
        self.budget_rules = config.scoring_tender.get('budget', {})
        self.relevance_rules = config.scoring_tender.get('relevance', {})
        self.timeliness_rules = config.scoring_tender.get('timeliness', {})
        self.completeness_rules = config.scoring_tender.get('completeness', {})
        self.decision_chain_rules = config.scoring_tender.get('decision_chain', {})
        self.institution_rules = config.scoring_tender.get('institution', {})
        self.history_rules = config.scoring_tender.get('history', {})
    
    def calculate_budget(self, lead: dict[str, Any]) -> int:
        """预算状态 (20%)"""
        budget_info = lead.get('budget_info', '') or ''
        
        if budget_info and any(k in budget_info for k in ['万元', '预算', '金额', '￥']):
            return self.budget_rules.get('confirmed', {}).get('score', 20)
        elif budget_info:
            return self.budget_rules.get('indicated', {}).get('score', 12)
        else:
            return self.budget_rules.get('unknown', {}).get('score', 5)
    
    def calculate_relevance(self, lead: dict[str, Any]) -> int:
        """匹配度 (20%)"""
        keywords = lead.get('keywords_matched', []) or []
        has_core = any(k for k in keywords if '免疫荧光' in k or 'Immunofluorescence' in k.lower())
        has_equipment = any(k for k in keywords if '显微镜' in k or 'Microscope' in k)
        
        if has_core and has_equipment:
            return self.relevance_rules.get('core_equipment', {}).get('score', 20)
        elif has_core:
            return self.relevance_rules.get('general_keywords', {}).get('score', 12)
        else:
            return self.relevance_rules.get('weak_match', {}).get('score', 4)
    
    def calculate_timeliness(self, lead: dict[str, Any]) -> int:
        """时效性 (20%)"""
        days = days_since(lead.get('published_at'))
        
        if days <= 90:
            return self.timeliness_rules.get('recent_90_days', {}).get('score', 20)
        elif days <= 180:
            return self.timeliness_rules.get('recent_180_days', {}).get('score', 12)
        else:
            return self.timeliness_rules.get('older', {}).get('score', 5)
    
    def calculate_completeness(self, lead: dict[str, Any]) -> int:
        """信息完备度 (15%)"""
        has_phone = bool(lead.get('phone'))
        has_email = bool(lead.get('email'))
        has_address = bool(lead.get('address'))
        org_only = lead.get('org_only', False)
        
        if org_only:
            return self.completeness_rules.get('org_only', {}).get('score', 3)
        elif not has_phone and has_email and has_address:
            return self.completeness_rules.get('no_phone', {}).get('score', 9)
        elif has_phone and has_email and has_address:
            return self.completeness_rules.get('full', {}).get('score', 15)
        else:
            return 3
    
    def calculate_decision_chain(self, lead: dict[str, Any]) -> int:
        """决策链条 (10%)"""
        has_pi = bool(lead.get('pi_name'))
        has_contact = bool(lead.get('name'))
        has_device_dept = bool(lead.get('device_dept'))
        
        if has_pi and has_contact and has_device_dept:
            return self.decision_chain_rules.get('full_chain', {}).get('score', 10)
        elif has_contact:
            return self.decision_chain_rules.get('contact_only', {}).get('score', 6)
        else:
            return self.decision_chain_rules.get('org_only', {}).get('score', 2)
    
    def calculate_institution(self, lead: dict[str, Any]) -> int:
        """机构类型 (10%)"""
        org = lead.get('organization', '') or ''
        
        # 985/211/双一流
        top_keywords = ['北京大学', '清华大学', '复旦大学', '上海交通大学', '浙江大学', '中科院']
        if any(k in org for k in top_keywords):
            return self.institution_rules.get('top_university', {}).get('score', 10)
        
        # 三甲医院
        if '医院' in org:
            return self.institution_rules.get('hospital_tier3', {}).get('score', 7)
        
        # 科研院所
        if '研究所' in org or '研究院' in org:
            return self.institution_rules.get('research_institute', {}).get('score', 10)
        
        return self.institution_rules.get('enterprise', {}).get('score', 4)
    
    def calculate_history(self, lead: dict[str, Any]) -> int:
        """历史互动 (5%)"""
        status = lead.get('feedback_status', '未处理')
        
        if status in ['已成交', '已报价']:
            return self.history_rules.get('closed', {}).get('score', 5)
        elif status in ['已流失']:
            return self.history_rules.get('lost', {}).get('score', 0)
        else:
            return self.history_rules.get('no_interaction', {}).get('score', 2)
    
    def calculate_score(self, lead: dict[str, Any]) -> int:
        """计算总分 (直接加权求和)"""
        score = (
            self.calculate_budget(lead) +
            self.calculate_relevance(lead) +
            self.calculate_timeliness(lead) +
            self.calculate_completeness(lead) +
            self.calculate_decision_chain(lead) +
            self.calculate_institution(lead) +
            self.calculate_history(lead)
        )
        return int(score)
