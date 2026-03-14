"""配置管理服务"""
from typing import Dict, Any
from pathlib import Path
import yaml
from src.config.loader import load_config
from src.logging_config import get_logger

logger = get_logger()


class ConfigService:
    """配置管理服务"""
    
    def __init__(self):
        self.config = load_config()
        self.config_dir = Path("config")
    
    async def get_keywords(self) -> Dict[str, Any]:
        """获取关键词配置"""
        try:
            keywords_file = self.config_dir / "keywords.yaml"
            with open(keywords_file, 'r', encoding='utf-8') as f:
                keywords = yaml.safe_load(f)
            
            logger.info("keywords_config_loaded", file=str(keywords_file))
            return keywords
        except Exception as e:
            logger.error("keywords_load_failed", error=str(e))
            return {}
    
    async def get_scoring_rules(self) -> Dict[str, Any]:
        """获取评分规则配置"""
        try:
            scoring_file = self.config_dir / "scoring_paper.yaml"
            with open(scoring_file, 'r', encoding='utf-8') as f:
                scoring = yaml.safe_load(f)
            
            logger.info("scoring_config_loaded", file=str(scoring_file))
            return scoring
        except Exception as e:
            logger.error("scoring_load_failed", error=str(e))
            return {}
    
    async def update_keywords(self, keywords: Dict[str, Any]) -> bool:
        """更新关键词配置"""
        try:
            keywords_file = self.config_dir / "keywords.yaml"
            
            # 备份原文件
            backup_file = keywords_file.with_suffix('.yaml.bak')
            if keywords_file.exists():
                import shutil
                shutil.copy(keywords_file, backup_file)
            
            # 写入新配置
            with open(keywords_file, 'w', encoding='utf-8') as f:
                yaml.dump(keywords, f, allow_unicode=True, default_flow_style=False)
            
            logger.info("keywords_updated", file=str(keywords_file))
            return True
        except Exception as e:
            logger.error("keywords_update_failed", error=str(e))
            return False
