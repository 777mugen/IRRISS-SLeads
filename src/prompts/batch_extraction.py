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

2. **🔴 中国作者识别规则（重要）**：
   - **判断标准**：单位地址包含以下关键词之一：
     * "China"、"中国"
     * 城市名："Beijing"、"Shanghai"、"Guangzhou"、"Shenzhen"、"Hangzhou"、"Nanjing"、"Wuhan"、"Chengdu"、"Xi'an"
     * 省份名："Beijing"、"Shanghai"、"Guangdong"、"Jiangsu"、"Zhejiang"
   
   - **通讯作者识别优先级**：
     * 优先级1：正文中标注的 "Corresponding Author" + **且是中国作者**
     * 优先级2：**第一个中国作者**（按作者顺序）
     * 优先级3：如果没有中国作者，提取第一个作者
   
   - **重要**：只提取中国人的信息作为通讯作者

3. **字段对应关系**：
   - "单位地址"、"联系电话"、"电子邮箱" 必须对应 "通讯作者" 这个字段的人
   - 不是其他作者的信息

4. **🔴 翻译要求（重要）**：
   - **institution** 字段：保留英文原文
   - **institution_cn** 字段：**必须翻译成中文**
     * 例如："Peking University" → "北京大学"
     * 例如："Tsinghua University" → "清华大学"
     * 例如："Fudan University" → "复旦大学"
   
   - **address** 字段：保留英文原文
   - **address_cn** 字段：**必须翻译成中文**
     * 例如："Beijing, China" → "中国北京"
     * 例如："123 Main St, Shanghai" → "上海主街123号"
   
   - **所有地址信息都需要提供中英文两个版本**

5. **作者信息合集格式**：
   - 包含所有作者（包括通讯作者）
   - 每个作者一行，用 \\n 换行
   - 格式：姓名 | 单位地址 | 联系电话 | 电子邮箱

6. **缺失值处理**：
   - 如果某个字段找不到，设为 null

论文内容：
{markdown_content}

---

**返回格式（JSON）**：
{{
  "title": "文章标题（来自正文，非 References）",
  "published_at": "YYYY-MM-DD 或 null",
  "corresponding_author": {{
    "name": "通讯作者姓名（第一个中国通讯作者，或第一个中国作者）",
    "email": "通讯作者的邮箱（对应上述姓名的人）",
    "phone": "通讯作者的联系电话（对应上述姓名的人）",
    "institution": "通讯作者的单位（英文原文）",
    "institution_cn": "通讯作者的单位（中文翻译）",
    "address": "通讯作者的单位地址（英文原文）",
    "address_cn": "通讯作者的单位地址（中文翻译）"
  }},
  "all_authors_info": "作者信息合集（每个作者一行，格式：姓名 | 单位地址 | 联系电话 | 电子邮箱）"
}}

**示例输出 1（中国作者）**：
{{
  "title": "Multiplex immunofluorescence detection...",
  "published_at": "2024-03-15",
  "corresponding_author": {{
    "name": "张三",
    "email": "zhang@pku.edu.cn",
    "phone": "+86-10-12345678",
    "institution": "Peking University",
    "institution_cn": "北京大学",
    "address": "Beijing, China",
    "address_cn": "中国北京"
  }},
  "all_authors_info": "张三 | Peking University | +86-10-12345678 | zhang@pku.edu.cn\\n李四 | Tsinghua University | +86-10-87654321 | li@tsinghua.edu.cn"
}}

**示例输出 2（外国作者）**：
{{
  "title": "Spatial proteomics analysis...",
  "published_at": "2024-02-20",
  "corresponding_author": {{
    "name": "John Doe",
    "email": "john@harvard.edu",
    "phone": "+1-617-1234567",
    "institution": "Harvard Medical School",
    "institution_cn": "哈佛医学院",
    "address": "Boston, MA, USA",
    "address_cn": "美国马萨诸塞州波士顿"
  }},
  "all_authors_info": "John Doe | Harvard Medical School | +1-617-1234567 | john@harvard.edu\\nJane Smith | MIT | +1-617-9876543 | jane@mit.edu"
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
