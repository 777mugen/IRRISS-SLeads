"""
ZAI API client for GLM-5 LLM.
ZAI API 客户端，用于 GLM-5 大模型调用。
"""

import asyncio
import json
from typing import Any, Optional

import httpx

from src.config import config
from src.llm.rate_limiter import get_rate_limiter


class ZAIClient:
    """
    ZAI API 客户端
    
    支持 zai/glm-5 模型
    """
    
    API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or config.zai_api_key
        self.model = model or config.zai_model
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        self._client = httpx.AsyncClient(timeout=120.0)
        self.rate_limiter = get_rate_limiter()
        self.logger = __import__('src.logging_config', fromlist=['get_logger']).get_logger()
        self._max_retries = 3
    
    async def close(self):
        """关闭客户端"""
        await self._client.aclose()
    
    async def chat(
        self, 
        message: str, 
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096
    ) -> str:
        """
        发送聊天请求
        
        Args:
            message: 用户消息
            system_prompt: 系统提示
            temperature: 温度参数
            max_tokens: 最大 token 数
            
        Returns:
            模型响应文本
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        # 重试逻辑
        last_error = None
        for attempt in range(self._max_retries):
            # 应用速率限制
            await self.rate_limiter.acquire()
            
            try:
                response = await self._client.post(
                    self.API_URL,
                    headers=self.headers,
                    json=payload
                )
                
                # 处理 429 错误
                if response.status_code == 429:
                    retry_after = float(response.headers.get('Retry-After', 60))
                    self.logger.warning(
                        f"GLM-5 API 限流 (429)，等待 {retry_after} 秒后重试 "
                        f"(尝试 {attempt + 1}/{self._max_retries})"
                    )
                    await asyncio.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                
                data = response.json()
                return data["choices"][0]["message"]["content"]
                
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429:
                    # 429 错误已经在上面处理
                    continue
                elif e.response.status_code >= 500:
                    # 服务器错误，等待后重试
                    wait_time = 5 * (attempt + 1)
                    self.logger.warning(
                        f"服务器错误 ({e.response.status_code})，等待 {wait_time} 秒后重试"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # 其他错误直接抛出
                    raise
            except Exception as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    wait_time = 5 * (attempt + 1)
                    self.logger.warning(f"请求失败: {e}，等待 {wait_time} 秒后重试")
                    await asyncio.sleep(wait_time)
                    continue
                raise
        
        # 所有重试都失败
        raise last_error or Exception("All retries failed")
    
    async def extract_json(
        self, 
        content: str, 
        prompt_template: str
    ) -> dict[str, Any]:
        """
        从内容中提取 JSON 结构化数据
        
        Args:
            content: 要提取的内容
            prompt_template: 提取提示模板
            
        Returns:
            解析后的 JSON 字典
        """
        full_prompt = f"{prompt_template}\n\n---\n\n{content}"
        
        response = await self.chat(full_prompt, temperature=0.1)
        
        # 尝试解析 JSON
        try:
            # 清理可能的 markdown 代码块
            cleaned = response.strip()
            
            # 处理 ```json ... ``` 格式
            if '```json' in cleaned:
                start = cleaned.find('```json') + 7
                end = cleaned.find('```', start)
                if end > start:
                    cleaned = cleaned[start:end].strip()
            elif cleaned.startswith('```'):
                # 处理 ``` ... ``` 格式
                start = cleaned.find('```') + 3
                end = cleaned.rfind('```')
                if end > start:
                    cleaned = cleaned[start:end].strip()
            
            # 移除可能的语言标识符
            lines = cleaned.split('\n')
            if lines and lines[0].strip() in ['json', 'JSON', '']:
                lines = lines[1:]
            cleaned = '\n'.join(lines).strip()
            
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            return {"error": f"Failed to parse JSON: {str(e)}", "raw_response": response}
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
