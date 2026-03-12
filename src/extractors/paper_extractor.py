"""
Paper lead extractor using GLM-5.
论文线索提取器（使用 GLM-5）。
"""

from typing import Any

from .base import BaseExtractor


class PaperExtractor(BaseExtractor):
    """论文线索提取器"""
    
    def get_prompt_template(self) -> str:
        return """你是一个专业的学术论文信息提取助手。

请从以下论文页面内容中提取以下字段，以 JSON 格式返回：

必填字段：
- title: 文章标题（字符串）
- pmid: PubMed 唯一标识符（数字字符串，通常在 URL 中）
- doi: DOI 标识符（字符串，格式如 10.xxxx/xxxxx，如无则为 null）

通讯作者信息（尽量提取）：
- corresponding_author: 通讯作者信息对象，包含：
  - name: 通讯作者姓名
  - email: 通讯作者邮箱
  - phone: 通讯作者电话
  - institution: 通讯作者所属机构
  - address: 通讯作者地址
  如无通讯作者信息则设为 null

其他字段：
- published_at: 发表时间，格式 YYYY-MM-DD（字符串）
- keywords_matched: 命中的关键词列表（数组）
- all_authors: 全部作者信息数组，每个作者包含 name, institution, email（如有）
- article_url: 文章的具体链接（通常是 PubMed 页面 URL）

特殊规则：
- 如果内容不是论文相关页面，请返回 {"error": "不是论文页面"}
- 尽力提取作者信息，优先提取通讯作者（Corresponding Author）

重要规则：
1. 只返回 JSON，不要有任何其他文字
2. 确保 JSON 格式正确
3. 邮箱地址请转小写
4. 去除字段值前后的空白字符"""

    def validate_required_fields(self, data: dict[str, Any]) -> bool:
        """验证必填字段 - 只需要标题和 PMID"""
        # 只要求标题和 PMID 是必填的
        return (data.get("title") is not None and 
                len(data.get("title", "")) > 0 and
                data.get("pmid") is not None)
