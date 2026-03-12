"""
Configuration loader for Sales Lead Discovery System.
配置加载器。
"""

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


# 加载环境变量（override=True 强制使用 .env 文件中的值）
load_dotenv(override=True)

# 配置文件目录
CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


def load_yaml(filename: str) -> dict[str, Any]:
    """加载 YAML 配置文件"""
    filepath = CONFIG_DIR / filename
    if not filepath.exists():
        return {}
    
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class Config:
    """配置管理类"""
    
    def __init__(self):
        self._keywords = None
        self._sources = None
        self._scoring_paper = None
        self._scoring_tender = None
        self._scheduler = None
    
    @property
    def keywords(self) -> dict:
        """关键词配置"""
        if self._keywords is None:
            self._keywords = load_yaml("keywords.yaml")
        return self._keywords
    
    @property
    def sources(self) -> dict:
        """数据源配置"""
        if self._sources is None:
            self._sources = load_yaml("sources.yaml")
        return self._sources
    
    @property
    def scoring_paper(self) -> dict:
        """论文评分配置"""
        if self._scoring_paper is None:
            self._scoring_paper = load_yaml("scoring_paper.yaml")
        return self._scoring_paper
    
    @property
    def scoring_tender(self) -> dict:
        """招标评分配置"""
        if self._scoring_tender is None:
            self._scoring_tender = load_yaml("scoring_tender.yaml")
        return self._scoring_tender
    
    @property
    def scheduler(self) -> dict:
        """调度配置"""
        if self._scheduler is None:
            self._scheduler = load_yaml("scheduler.yaml")
        return self._scheduler
    
    @property
    def database_url(self) -> str:
        """数据库 URL"""
        return os.getenv("DATABASE_URL", "postgresql+asyncpg://localhost/sleads_dev")
    
    @property
    def jina_api_key(self) -> str:
        """Jina API Key"""
        return os.getenv("JINA_API_KEY", "")
    
    @property
    def zai_api_key(self) -> str:
        """ZAI API Key (GLM-5)"""
        return os.getenv("ZAI_API_KEY", "")
    
    @property
    def zai_model(self) -> str:
        """ZAI Model"""
        return os.getenv("ZAI_MODEL", "glm-5")
    
    @property
    def anthropic_api_key(self) -> str:
        """Anthropic API Key (deprecated, use zai)"""
        return os.getenv("ANTHROPIC_API_KEY", "")
    
    @property
    def log_level(self) -> str:
        """日志级别"""
        return os.getenv("LOG_LEVEL", "INFO")
    
    @property
    def feishu_webhook(self) -> str:
        """飞书机器人 Webhook URL"""
        return os.getenv("FEISHU_WEBHOOK", "")
    
    @property
    def tender_keywords(self) -> list[str]:
        """招标关键词"""
        # 从环境变量或配置文件获取
        env_keywords = os.getenv("TENDER_KEYWORDS", "")
        if env_keywords:
            return [k.strip() for k in env_keywords.split(",") if k.strip()]
        
        # 从配置文件获取
        if self.keywords and "tender" in self.keywords:
            return self.keywords["tender"]
        
        return []


# 全局配置实例
config = Config()
