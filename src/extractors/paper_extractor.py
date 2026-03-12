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
- name: 通讯作者或第一作者姓名（字符串）
- institution: 作者所属机构/单位（字符串）
- address: 机构地址（字符串）
- email: 通讯作者邮箱（字符串）
- published_at: 发表时间，格式 YYYY-MM-DD（字符串）

可选字段：
- phone: 联系电话（字符串，如无则为 null）
- keywords_matched: 命中的关键词列表（数组）

特殊字段：
- 如果某个必填字段无法从内容中提取，请设置为 null
- 如果内容不是论文相关页面，请返回 {"error": "不是论文页面"}

重要规则：
1. 只返回 JSON，不要有任何其他文字
2. 确保 JSON 格式正确
3. 邮箱地址请转小写
4. 去除字段值前后的空白字符"""

    def validate_required_fields(self, data: dict[str, Any]) -> bool:
        """验证必填字段"""
        required = ["title", "name", "institution", "address", "email"]
        return all(data.get(field) is not None for field in required)
