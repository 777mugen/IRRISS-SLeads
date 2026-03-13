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

   **A. 姓名判断（中文拼音规则）**：
   - 姓名由 1-4 个部分组成，用空格分隔
   - 每个部分首字母大写，其余字母小写
   - 示例：Wei Zhang, Xiaohong Wang, Ouyang Ming
   - **支持复姓**（视为一个整体）：
     * Ouyang, Zhuge, Sima, Dugu, Murong, Shangguan, Situ, Tai Shih, Gongye, Duanmu, Huyan, Ximen, Nangong, Liangqiu, Zuoqiu, Dongfang, Helian, Yuchi, Wenyuan, Tantai
   - 示例：
     * "Ouyang Ming" = 2 个部分（Ouyang + Ming）
     * "Sima Guang" = 2 个部分（Sima + Guang）
     * "Zhuge Liang" = 2 个部分（Zhuge + Liang）
   
   **B. 地址判断（中国机构）**：
   - 地址字段包含以下关键词之一（不区分大小写）：
     * **国家**：china, chinese
     * **主要城市**：beijing, shanghai, guangzhou, shenzhen, tianjin, chongqing
     * **省会/重点城市**：nanjing, wuhan, chengdu, xi'an, hangzhou, shenyang, changchun, harbin, jinan, zhengzhou, hefei, fuzhou, nanchang, changsha, guiyang, kunming, lanzhou, xining, yinchuan, urumqi, nanning, haikou, shijiazhuang, taiyuan, hohhot, lhasa, macau, hong kong
     * **机构特征**：university, institute, hospital, academy, college, school（需结合上述地点判断）
   
   **C. 组合判断规则**：
   - **同时满足**：姓名符合中文拼音规则 **且** 地址包含中国关键词 → 视为中国作者
   - **通讯作者识别优先级**：
     * 优先级1：正文标注的 "Corresponding Author" + **且是中国作者**
     * 优先级2：**第一个中国作者**（按作者顺序）
     * 优先级3：如果没有中国作者，提取第一个作者
   
   **D. 排除规则**：
   - 地址包含 "USA"、"UK"、"Japan" 等其他国家，**同时包含 "China"** → 仍视为中国（如 "China-USA 联合研究所"）
   - 地址明确包含其他国家且**不包含**中国关键词 → 即使姓名像中文也排除

3. **字段对应关系**：
   - "address"、"联系电话"、"电子邮箱" 必须对应 "通讯作者" 这个字段的人
   - 不是其他作者的信息

4. **🔴 翻译要求（重要）**：
   - **institution** 字段：保留英文原文
   - **address** 字段：**翻译成中文，合并单位和地址**
     * 格式："单位中文名，地址中文翻译"
     * 例如："Peking University, Beijing, China" → "北京大学，中国北京"
     * 例如："Tsinghua University, Haidian District, Beijing" → "清华大学，北京市海淀区"
     * 例如："Harvard Medical School, Boston, MA, USA" → "哈佛医学院，美国马萨诸塞州波士顿"
   
   - **address 字段必须包含单位中文名 + 地址中文翻译**

5. **作者信息合集格式**：
   - 包含所有作者（包括通讯作者）
   - 每个作者一行，用 \\n 换行
   - **all_authors_info**：格式：姓名 | 单位地址 | 联系电话 | 电子邮箱（保留英文原文）
   - **all_authors_info_cn**：格式：姓名 | 单位地址中文翻译 | 联系电话 | 电子邮箱

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
    "address": "通讯作者的单位地址（中文，格式：单位中文名，地址中文翻译）"
  }},
  "all_authors_info": "作者信息合集（每个作者一行，格式：姓名 | 单位地址 | 联系电话 | 电子邮箱）",
  "all_authors_info_cn": "作者信息合集中文版（每个作者一行，格式：姓名 | 单位地址中文翻译 | 联系电话 | 电子邮箱）"
}}

**示例输出 1（中国作者）**：
{{
  "title": "Multiplex immunofluorescence detection...",
  "published_at": "2024-03-15",
  "corresponding_author": {{
    "name": "Wei Zhang",
    "email": "zhang@pku.edu.cn",
    "phone": "+86-10-12345678",
    "institution": "Peking University",
    "address": "北京大学，中国北京"
  }},
  "all_authors_info": "Wei Zhang | Peking University, Beijing, China | +86-10-12345678 | zhang@pku.edu.cn\\nXiaohong Wang | Tsinghua University, Beijing, China | +86-10-87654321 | wang@tsinghua.edu.cn",
  "all_authors_info_cn": "张伟 | 北京大学，中国北京 | +86-10-12345678 | zhang@pku.edu.cn\\n王小红 | 清华大学，中国北京 | +86-10-87654321 | wang@tsinghua.edu.cn"
}}

**示例输出 2（复姓作者）**：
{{
  "title": "Spatial proteomics analysis...",
  "published_at": "2024-02-20",
  "corresponding_author": {{
    "name": "Ouyang Ming",
    "email": "ouyang@fudan.edu.cn",
    "phone": "+86-21-12345678",
    "institution": "Fudan University",
    "address": "复旦大学，中国上海"
  }},
  "all_authors_info": "Ouyang Ming | Fudan University, Shanghai, China | +86-21-12345678 | ouyang@fudan.edu.cn",
  "all_authors_info_cn": "欧阳明 | 复旦大学，中国上海 | +86-21-12345678 | ouyang@fudan.edu.cn"
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
