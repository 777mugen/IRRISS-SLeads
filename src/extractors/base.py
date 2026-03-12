"""
Base extractor for LLM-based field extraction.
LLM 字段提取器基类。
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from src.config import config
from src.llm import ZAIClient


class BaseExtractor(ABC):
    """
    字段提取器基类
    
    使用 GLM-5 API 从 Markdown 内容中提取结构化字段
    """
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.client = ZAIClient(api_key=api_key or config.zai_api_key, model=model or config.zai_model)
    
    async def close(self):
        """关闭客户端"""
        await self.client.close()
    
    @abstractmethod
    def get_prompt_template(self) -> str:
        """获取提取 Prompt 模板"""
        pass
    
    @abstractmethod
    def validate_required_fields(self, data: dict[str, Any]) -> bool:
        """验证必填字段是否完整"""
        pass
    
    async def extract(self, content: str) -> dict[str, Any]:
        """
        从 Markdown 内容中提取结构化字段
        
        Args:
            content: Markdown 格式的网页内容
            
        Returns:
            提取的结构化数据字典
        """
        prompt = self.get_prompt_template()
        
        result = await self.client.extract_json(content, prompt)
        
        if result.get("error"):
            return result
        
        # 验证必填字段
        if not self.validate_required_fields(result):
            result["_validation_error"] = "缺少必填字段"
        
        return result
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
