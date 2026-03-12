"""
Two-Stage Extractor
两阶段提取器

解决超长文本上下文溢出问题：
- Stage 1: 定位关键信息位置
- Stage 2: 提取指定区域内容
"""

from typing import Dict, Optional
import json

from src.llm.client import ZaiClient
from src.logging_config import get_logger


class TwoStageExtractor:
    """
    两阶段提取器
    
    适用于超长文本（>10000 字符）
    通过两阶段调用避免上下文溢出
    """
    
    def __init__(self):
        self.logger = get_logger()
        self.llm = ZaiClient()
    
    async def close(self):
        """关闭资源"""
        await self.llm.close()
    
    async def extract(self, markdown: str) -> Optional[Dict]:
        """
        两阶段提取
        
        Args:
            markdown: Markdown 内容
            
        Returns:
            提取的结构化数据
            
        Example:
            >>> extractor = TwoStageExtractor()
            >>> result = await extractor.extract(long_markdown)
            >>> result
            {
                'title': 'Article Title',
                'corresponding_author': {
                    'name': 'John Doe',
                    'email': 'john@example.com',
                    'phone': '+1-123-456-7890',
                    'institution': 'University',
                    'address': '123 Street'
                }
            }
        """
        # 检查文本长度
        if len(markdown) < 5000:
            # 短文本直接提取
            self.logger.debug("文本较短，使用单阶段提取")
            return await self._single_stage_extract(markdown)
        
        self.logger.info(f"长文本处理: {len(markdown)} 字符，使用两阶段提取")
        
        # Stage 1: 定位
        locations = await self._locate_keywords(markdown)
        
        if not locations:
            self.logger.warning("定位失败，回退到单阶段提取")
            return await self._single_stage_extract(markdown)
        
        # Stage 2: 提取
        result = await self._extract_fields(markdown, locations)
        
        return result
    
    async def _locate_keywords(self, markdown: str) -> Optional[Dict]:
        """
        阶段1: 定位关键词位置
        
        Args:
            markdown: Markdown 内容
            
        Returns:
            {
                'correspondence_start': <行号>,
                'correspondence_end': <行号>,
                'email_start': <行号>,
                'affiliation_start': <行号>
            }
        """
        # 只发送前 5000 字符用于定位
        text_for_location = markdown[:5000]
        
        prompt = f"""在以下 Markdown 文本中，找到以下关键词出现的**行号位置**：

关键词列表：
- Correspondence / Corresponding Author / 通讯作者
- Affiliation / 机构 / 单位
- Email / E-mail / 邮箱
- Phone / Telephone / 电话

请返回 JSON 格式：
{{
  "correspondence_start": <行号，从0开始>,
  "correspondence_end": <行号>,
  "affiliation_start": <行号>,
  "email_start": <行号>,
  "phone_start": <行号>
}}

**重要**:
1. 只返回 JSON，不要有任何其他文字
2. 如果找不到某个关键词，对应字段设为 null
3. 行号从 0 开始计数

文本内容（前5000字符）：
{text_for_location}
"""
        
        try:
            response = await self.llm.call(prompt)
            
            # 解析 JSON
            locations = json.loads(response)
            
            self.logger.info(f"定位成功: {locations}")
            return locations
            
        except json.JSONDecodeError as e:
            self.logger.error(f"定位阶段 JSON 解析失败: {e}")
            return None
        except Exception as e:
            self.logger.error(f"定位阶段失败: {e}")
            return None
    
    async def _extract_fields(
        self,
        markdown: str,
        locations: Dict
    ) -> Optional[Dict]:
        """
        阶段2: 提取指定区域内容
        
        Args:
            markdown: 完整 Markdown 内容
            locations: 位置信息
            
        Returns:
            结构化提取结果
        """
        lines = markdown.split('\n')
        
        # 提取通讯作者区域
        start = locations.get('correspondence_start')
        end = locations.get('correspondence_end')
        
        if start is None:
            start = 0
        if end is None:
            end = min(start + 50, len(lines))
        
        correspondence_section = '\n'.join(lines[start:end])
        
        # 如果区域仍然太长，截断
        if len(correspondence_section) > 3000:
            correspondence_section = correspondence_section[:3000]
        
        prompt = f"""从以下文本片段中提取通讯作者信息：

文本片段：
{correspondence_section}

请返回 JSON 格式：
{{
  "corresponding_author": {{
    "name": "通讯作者姓名",
    "email": "邮箱（转小写）",
    "phone": "电话",
    "institution": "单位",
    "address": "地址"
  }}
}}

**重要**:
1. 只返回 JSON，不要有任何其他文字
2. 如果某个字段找不到，设为 null
3. 邮箱地址必须转小写
4. 去除字段值前后的空白字符
"""
        
        try:
            response = await self.llm.call(prompt)
            
            # 解析 JSON
            result = json.loads(response)
            
            # 验证结果
            if 'corresponding_author' not in result:
                self.logger.warning("提取结果缺少 corresponding_author 字段")
                return None
            
            self.logger.info("两阶段提取成功")
            return result
            
        except json.JSONDecodeError as e:
            self.logger.error(f"提取阶段 JSON 解析失败: {e}")
            return None
        except Exception as e:
            self.logger.error(f"提取阶段失败: {e}")
            return None
    
    async def _single_stage_extract(self, markdown: str) -> Optional[Dict]:
        """
        单阶段提取（用于短文本或回退）
        
        Args:
            markdown: Markdown 内容
            
        Returns:
            结构化提取结果
        """
        # 截断过长文本
        if len(markdown) > 8000:
            markdown = markdown[:8000]
        
        prompt = f"""从以下论文 Markdown 内容中提取通讯作者信息：

内容：
{markdown}

请返回 JSON 格式：
{{
  "corresponding_author": {{
    "name": "通讯作者姓名",
    "email": "邮箱",
    "phone": "电话",
    "institution": "单位",
    "address": "地址"
  }}
}}

**重要**:
1. 只返回 JSON
2. 找不到的字段设为 null
3. 邮箱转小写
"""
        
        try:
            response = await self.llm.call(prompt)
            result = json.loads(response)
            return result
        except Exception as e:
            self.logger.error(f"单阶段提取失败: {e}")
            return None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
