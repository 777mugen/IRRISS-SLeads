"""
Paper lead scorer.
论文线索评分引擎。
"""

from typing import Any

from src.config import config
from .base import BaseScorer, days_since


class PaperScorer(BaseScorer):
    """论文线索评分引擎"""
    
    def __init__(self):
        self.weights = config.scoring_paper.get('weights', {})
        self.completeness_rules = config.scoring_paper.get('completeness', {})
        self.relevance_rules = config.scoring_paper.get('relevance', {})
        self.timeliness_rules = config.scoring_paper.get('timeliness', {})
        self.decision_chain_rules = config.scoring_paper.get('decision_chain', {})
        self.institution_rules = config.scoring_paper.get('institution', {})
        self.history_rules = config.scoring_paper.get('history', {})
    
    def calculate_completeness(self, lead: dict[str, Any]) -> int:
        """信息完备度 (20%)"""
        has_phone = bool(lead.get('phone'))
        has_email = bool(lead.get('email'))
        has_address = bool(lead.get('address'))
        org_only = lead.get('org_only', False)
        
        if org_only:
            return self.completeness_rules.get('org_only', {}).get('score', 5)
        elif not has_phone and has_email and has_address:
            return self.completeness_rules.get('no_phone', {}).get('score', 12)
        elif has_phone and has_email and has_address:
            return self.completeness_rules.get('full', {}).get('score', 20)
        else:
            return 5
    
    def calculate_relevance(self, lead: dict[str, Any]) -> int:
        """匹配度 (25%)"""
        keywords = lead.get('keywords_matched', []) or []
        has_core = any(k for k in keywords if k in ['Multiplex Immunofluorescence', 'mIF', 'TSA', 'CODEX'])
        has_equipment = any(k for k in keywords if k in ['Confocal', 'Fluorescence Microscope'])
        
        if has_core and has_equipment:
            return self.relevance_rules.get('core_equipment', {}).get('score', 25)
        elif has_core:
            return self.relevance_rules.get('general_keywords', {}).get('score', 15)
        else:
            return self.relevance_rules.get('weak_match', {}).get('score', 5)
    
    def calculate_timeliness(self, lead: dict[str, Any]) -> int:
        """时效性 (20%)"""
        days = days_since(lead.get('published_at'))
        
        if days <= 90:
            return self.timeliness_rules.get('recent_90_days', {}).get('score', 20)
        elif days <= 180:
            return self.timeliness_rules.get('recent_180_days', {}).get('score', 12)
        else:
            return self.timeliness_rules.get('older', {}).get('score', 5)
    
    def calculate_decision_chain(self, lead: dict[str, Any]) -> int:
        """决策链条 (15%)"""
        has_pi = bool(lead.get('pi_name'))
        has_corresponding = bool(lead.get('corresponding_author'))
        has_contact = bool(lead.get('name'))
        
        if has_pi and has_corresponding:
            return self.decision_chain_rules.get('pi_corresponding', {}).get('score', 15)
        elif has_contact:
            return self.decision_chain_rules.get('contact_only', {}).get('score', 9)
        else:
            return self.decision_chain_rules.get('org_only', {}).get('score', 3)
    
    def calculate_institution(self, lead: dict[str, Any]) -> int:
        """机构类型 (10%)"""
        institution = lead.get('institution', '') or ''
        institution_lower = institution.lower()
        
        # 985/211/双一流
        top_keywords = ['北京大学', '清华大学', '复旦大学', '上海交通大学', '浙江大学', 
                       '中国科学技术大学', '南京大学', '武汉大学', '中山大学', '中科院']
        if any(k in institution for k in top_keywords):
            return self.institution_rules.get('top_university', {}).get('score', 10)
        
        # 三甲医院
        if '医院' in institution and ('三甲' in institution or '第一' in institution or '附属' in institution):
            return self.institution_rules.get('hospital_tier3', {}).get('score', 7)
        
        # 科研院所
        if '研究所' in institution or '研究院' in institution:
            return self.institution_rules.get('research_institute', {}).get('score', 10)
        
        return self.institution_rules.get('enterprise', {}).get('score', 4)
    
    def calculate_history(self, lead: dict[str, Any]) -> int:
        """历史互动 (10%)"""
        status = lead.get('feedback_status', '未处理')
        
        if status in ['已成交']:
            return self.history_rules.get('closed', {}).get('score', 10)
        elif status in ['已报价']:
            return self.history_rules.get('quoted', {}).get('score', 10)
        elif status in ['已流失']:
            return self.history_rules.get('lost', {}).get('score', 0)
        else:
            return self.history_rules.get('no_interaction', {}).get('score', 5)
    
    def calculate_score(self, lead: dict[str, Any]) -> int:
        """计算总分 (直接加权求和)"""
        # 每个维度的满分已经按权重设置，直接相加即可
        score = (
            self.calculate_completeness(lead) +
            self.calculate_relevance(lead) +
            self.calculate_timeliness(lead) +
            self.calculate_decision_chain(lead) +
            self.calculate_institution(lead) +
            self.calculate_history(lead)
        )
        return int(score)
