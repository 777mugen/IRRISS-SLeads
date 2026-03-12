"""
Tender lead extractor using GLM-5.
招标线索提取器（使用 GLM-5）。
"""

from typing import Any

from .base import BaseExtractor


class TenderExtractor(BaseExtractor):
    """招标线索提取器"""
    
    def get_prompt_template(self) -> str:
        return """你是一个专业的招标公告信息提取助手。

请从以下招标公告页面内容中提取以下字段，以 JSON 格式返回：

必填字段：
- project_name: 项目名称（字符串）
- organization: 招标单位（字符串）
- address: 单位地址（字符串）
- published_at: 发生时间，格式 YYYY-MM-DD（字符串）

可选字段：
- name: 联系人姓名（字符串，如无则为 null）
- email: 联系邮箱（字符串，如无则为 null）
- phone: 联系电话（字符串，如无则为 null）
- budget_info: 预算信息（字符串，如无则为 null）
- announcement_id: 公告编号（字符串，如无则为 null）

特殊字段：
- org_only: 是否仅有单位信息（布尔值，如果没有具体联系人则设为 true）

重要规则：
1. 只返回 JSON，不要有任何其他文字
2. 确保 JSON 格式正确
3. 邮箱地址请转小写
4. 如果没有具体联系人（name 字段为空），必须设置 org_only: true
5. 如果内容不是招标公告相关页面，请返回 {"error": "不是招标公告页面"}"""

    def validate_required_fields(self, data: dict[str, Any]) -> bool:
        """验证必填字段"""
        # 项目名称和组织是必须的
        if not data.get("project_name") or not data.get("organization"):
            return False
        # 要么有邮箱，要么标记 org_only
        if not data.get("email") and not data.get("org_only"):
            return False
        return True
