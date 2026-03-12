"""
Batch Extraction Prompts
批量提取的 Prompt 模板
"""

# 主提取 Prompt
BATCH_EXTRACTION_PROMPT_V1 = """从以下论文内容中提取信息，以 JSON 格式返回。

**🔴 严格遵守规则**：

1. **绝对不要提取 References 部分的任何信息**：
   - References 中的作者姓名、单位、联系方式
   - References 中的文章标题、DOI
   - References 中的任何其他信息
   - 只提取正文内容（References 之前的部分）

2. **通讯作者识别优先级**：
   - 优先级1：正文明确标注的 "Corresponding Author"、"Correspondence to"、"通讯作者"
   - 优先级2：如果有多个通讯作者，只提取**第一个**
   - 优先级3：如果没有标注通讯作者，提取所有作者中的**第一个作者**

3. **字段对应关系**：
   - "单位地址"、"联系电话"、"电子邮箱" 必须对应 "通讯作者" 这个字段的人
   - 不是其他作者的信息

4. **作者信息合集格式**：
   - 包含所有作者（包括通讯作者）
   - 每个作者一行，用 \\n 换行
   - 格式：姓名 | 单位地址 | 联系电话 | 电子邮箱

5. **缺失值处理**：
   - 如果某个字段找不到，设为 null

论文内容：
{markdown_content}

---

**返回格式（JSON）**：
{{
  "title": "文章标题（来自正文，非 References）",
  "published_at": "YYYY-MM-DD 或 null",
  "corresponding_author": {{
    "name": "通讯作者姓名（第一个通讯作者，或第一个作者）",
    "email": "通讯作者的邮箱（对应上述姓名的人）",
    "phone": "通讯作者的联系电话（对应上述姓名的人）",
    "address": "通讯作者的单位地址（对应上述姓名的人）"
  }},
  "all_authors_info": "作者信息合集（每个作者一行，格式：姓名 | 单位地址 | 联系电话 | 电子邮箱）"
}}

**示例输出**：
{{
  "title": "Multiplex immunofluorescence detection...",
  "published_at": "2024-03-15",
  "corresponding_author": {{
    "name": "John Doe",
    "email": "john.doe@example.com",
    "phone": "+1-123-456-7890",
    "address": "Department of Pathology, Harvard Medical School, Boston, MA, USA"
  }},
  "all_authors_info": "John Doe | Department of Pathology, Harvard Medical School | +1-123-456-7890 | john.doe@example.com\\nJane Smith | Department of Biology, MIT | +1-234-567-8901 | jane.smith@mit.edu\\nBob Johnson | Department of Chemistry, Stanford | +1-345-678-9012 | bob.johnson@stanford.edu"
}}

**只返回 JSON，不要有任何其他文字。**
"""

# 备用简化 Prompt（如果 V1 效果不佳）
BATCH_EXTRACTION_PROMPT_V2 = """提取论文信息，以 JSON 格式返回。

⚠️ **重要**：只提取正文内容，不要提取 References 部分。

论文内容：
{markdown_content}

返回 JSON：
{{
  "title": "标题",
  "published_at": "YYYY-MM-DD 或 null",
  "corresponding_author": {{
    "name": "通讯作者姓名",
    "email": "邮箱",
    "phone": "电话",
    "institution": "单位",
    "address": "地址"
  }}
}}

只返回 JSON，不要其他文字。
"""

# 字段补齐 Prompt（用于重新提取缺失字段）
FIELD_COMPLETION_PROMPT = """从以下论文内容中提取缺失的字段，以 JSON 格式返回。

**缺失字段**：{missing_fields}

**重要**：
1. 只提取正文内容，不要提取 References 部分
2. 如果找不到，设为 null

论文内容：
{markdown_content}

返回 JSON（只包含缺失字段）：
{json_template}

只返回 JSON，不要其他文字。
"""


def get_prompt(version: str = "v1") -> str:
    """
    获取指定版本的 Prompt
    
    Args:
        version: Prompt 版本（v1 或 v2）
        
    Returns:
        Prompt 模板
    """
    prompts = {
        "v1": BATCH_EXTRACTION_PROMPT_V1,
        "v2": BATCH_EXTRACTION_PROMPT_V2
    }
    
    return prompts.get(version, prompts["v1"])
