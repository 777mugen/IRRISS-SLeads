"""
Base scorer for lead scoring.
评分引擎基类。
"""

from abc import ABC, abstractmethod
from datetime import date, timedelta
from typing import Any


class BaseScorer(ABC):
    """评分引擎基类"""
    
    GRADE_THRESHOLDS = {
        'A': 80,
        'B': 65,
        'C': 50,
        'D': 0,
    }
    
    def score_to_grade(self, score: int) -> str:
        """将数值分数转换为等级"""
        if score >= self.GRADE_THRESHOLDS['A']:
            return 'A'
        elif score >= self.GRADE_THRESHOLDS['B']:
            return 'B'
        elif score >= self.GRADE_THRESHOLDS['C']:
            return 'C'
        else:
            return 'D'
    
    @abstractmethod
    def calculate_completeness(self, lead: dict[str, Any]) -> int:
        """计算信息完备度分数"""
        pass
    
    @abstractmethod
    def calculate_relevance(self, lead: dict[str, Any]) -> int:
        """计算匹配度分数"""
        pass
    
    @abstractmethod
    def calculate_timeliness(self, lead: dict[str, Any]) -> int:
        """计算时效性分数"""
        pass
    
    @abstractmethod
    def calculate_score(self, lead: dict[str, Any]) -> int:
        """计算总分"""
        pass
    
    def score_lead(self, lead: dict[str, Any]) -> tuple[int, str]:
        """
        评分并返回分数和等级
        
        Returns:
            (score, grade) 元组
        """
        score = self.calculate_score(lead)
        grade = self.score_to_grade(score)
        return score, grade


def days_since(date_value: date | None) -> int:
    """计算距离今天的天数"""
    if date_value is None:
        return 9999  # 未知日期视为很久以前
    delta = date.today() - date_value
    return delta.days
