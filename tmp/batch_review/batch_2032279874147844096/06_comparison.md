# 批处理文件对比 - 新旧 Prompt 版本

**创建时间**: 2026-03-13 11:42

---

## 📊 文件对比

| 文件 | 大小 | Prompt 版本 | 说明 |
|------|------|-------------|------|
| `01_input.jsonl` | 1.4 MB | 简化版（旧） | 实际使用的版本（缺少关键特性） |
| `05_input_new_prompt.jsonl` | 1.5 MB | 完整版（新） | 修复后的版本（包含所有特性） |

---

## 🔍 Prompt 内容对比

### 旧版 Prompt（01_input.jsonl）

**特点**:
- ❌ **缺少中国作者识别规则**
- ❌ **缺少地址翻译要求**（`address_cn`）
- ❌ **缺少多单位换行格式**
- ❌ **缺少复姓支持**
- ❌ **缺少示例输出**

**内容预览**:
```
提取论文信息，以 JSON 格式返回。

⚠️ **重要**：只提取正文内容，不要提取 References 部分。

论文内容：
{markdown_content}

返回 JSON：
{
  "title": "标题",
  "published_at": "YYYY-MM-DD",
  "corresponding_author": {
    "name": "通讯作者姓名",
    "email": "邮箱",
    "phone": "电话",
    "institution": "单位",
    "address": "地址"
  }
}
```

**长度**: ~500 字符

---

### 新版 Prompt（05_input_new_prompt.jsonl）

**特点**:
- ✅ **中国作者识别规则**（姓名拼音 + 地址关键词）
- ✅ **地址翻译要求**（英文 `address` + 中文 `address_cn`）
- ✅ **多单位换行格式**（`\n` 分隔，上标 `¹²³` 标记）
- ✅ **复姓支持**（Ouyang, Zhuge, Sima 等 20+ 复姓）
- ✅ **详细示例**（双单位 + 三单位）
- ✅ **all_authors_info_cn 字段**

**内容预览**:
```
从以下论文内容中提取信息，以 JSON 格式返回。

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
   
   - **address** 字段：**保留英文原文**（多单位换行）
     * 格式：每个单位单独一行，用 \n 换行
     * 格式：¹科室 → 机构 → 城市 → 邮编 → 国家
     * 示例：
       ```
       ¹Department of Cardiology, West China Hospital, Sichuan University, Chengdu 610041, China
       ²Department of Cardiology, Sichuan Provincial People's Hospital, Chengdu 610072, China
       ```
   
   - **address_cn** 字段：**翻译成中文**（多单位换行）
     * 格式：每个单位单独一行，用 \n 换行
     * 格式：¹科室中文 → 机构中文 → 城市中文 → 邮编 → 国家中文
     * 示例：
       ```
       ¹四川大学华西医院心内科，成都 610041，中国
       ²四川省人民医院心内科，成都 610072，中国
       ```
   
   - **重要**：address 和 address_cn 必须对应，行数相同

5. **作者信息合集格式**：
   - 包含所有作者（包括通讯作者）
   - 每个作者一行，用 \n 换行
   - **all_authors_info**：格式：姓名 | 单位地址（英文） | 联系电话 | 电子邮箱
   - **all_authors_info_cn**：格式：姓名 | 单位地址（中文翻译） | 联系电话 | 电子邮箱

6. **缺失值处理**：
   - 如果某个字段找不到，设为 null

---

**返回格式（JSON）**：
{
  "title": "文章标题（来自正文，非 References）",
  "published_at": "YYYY-MM-DD 或 null",
  "corresponding_author": {
    "name": "通讯作者姓名（第一个中国通讯作者，或第一个中国作者）",
    "email": "通讯作者的邮箱（对应上述姓名的人）",
    "phone": "通讯作者的联系电话（对应上述姓名的人）",
    "institution": "通讯作者的单位（英文原文）",
    "address": "通讯作者的单位地址（英文原文，多单位换行）",
    "address_cn": "通讯作者的单位地址（中文翻译，多单位换行）"
  },
  "all_authors_info": "作者信息合集（每个作者一行，格式：姓名 | 单位地址英文 | 联系电话 | 电子邮箱）",
  "all_authors_info_cn": "作者信息合集中文版（每个作者一行，格式：姓名 | 单位地址中文翻译 | 联系电话 | 电子邮箱）"
}

**示例输出 1（双单位中国作者）**：
{
  "title": "Multiplex immunofluorescence detection of tumor microenvironment...",
  "published_at": "2024-03-15",
  "corresponding_author": {
    "name": "Wei Zhang",
    "email": "zhang@scu.edu.cn",
    "phone": "+86-28-85422141",
    "institution": "West China Hospital, Sichuan University",
    "address": "¹Department of Cardiology, West China Hospital, Sichuan University, Chengdu 610041, China\n²Department of Cardiology, Sichuan Provincial People's Hospital, Chengdu 610072, China",
    "address_cn": "¹四川大学华西医院心内科，成都 610041，中国\n²四川省人民医院心内科，成都 610072，中国"
  },
  "all_authors_info": "Wei Zhang | ¹Department of Cardiology, West China Hospital, Sichuan University, Chengdu 610041, China\n²Department of Cardiology, Sichuan Provincial People's Hospital, Chengdu 610072, China | +86-28-85422141 | zhang@scu.edu.cn\nXiaohong Wang | Department of Oncology, Peking University Third Hospital, Beijing 100191, China | +86-10-82265714 | wang@pku.edu.cn",
  "all_authors_info_cn": "张伟 | ¹四川大学华西医院心内科，成都 610041，中国\n²四川省人民医院心内科，成都 610072，中国 | +86-28-85422141 | zhang@scu.edu.cn\n王小红 | 北京大学第三医院肿瘤科，北京 100191，中国 | +86-10-82265714 | wang@pku.edu.cn"
}
```

**长度**: ~3000 字符（6 倍于旧版）

---

## 📊 关键差异总结

| 特性 | 旧版 Prompt | 新版 Prompt |
|------|-------------|-------------|
| **中国作者识别** | ❌ 缺失 | ✅ 姓名 + 地址组合判断 |
| **地址翻译** | ❌ 缺失 | ✅ 英文 + 中文双语 |
| **多单位格式** | ❌ 缺失 | ✅ 换行分隔 + 上标 |
| **复姓支持** | ❌ 缺失 | ✅ 20+ 复姓列表 |
| **示例输出** | ❌ 缺失 | ✅ 2 个真实示例 |
| **字段完整性** | ❌ 5 个字段 | ✅ 7 个字段（新增 address_cn, all_authors_info_cn） |
| **Prompt 长度** | ~500 字符 | ~3000 字符 |

---

## 🎯 使用建议

### 如何提交新批处理任务

**步骤 1**: 上传文件
```bash
cd /Users/irriss/Git/IRRISS/IRRISS-SLeads
. .venv/bin/activate
PYTHONPATH=/Users/irriss/Git/IRRISS/IRRISS-SLeads python3 << 'EOF'
import asyncio
from src.pipeline_batch import BatchPipeline

async def submit():
    pipeline = BatchPipeline()
    
    # 使用新批处理文件
    from pathlib import Path
    batch_file = Path("tmp/batch_review/batch_2032279874147844096/05_input_new_prompt.jsonl")
    
    result = await pipeline.submit_batch_from_file(
        batch_file=batch_file,
        wait_for_completion=False
    )
    
    print(f"批次 ID: {result.get('batch_id')}")

asyncio.run(submit())
EOF
```

**步骤 2**: 等待处理完成（约 30-40 分钟）

**步骤 3**: 对比结果
- 对比旧版结果（02_output.jsonl）
- 验证 address_cn 字段是否生成
- 验证中国作者识别是否准确

---

## 📝 修复说明

**Bug 根源**:
- `src/processors/batch_processor.py` 使用了硬编码的简化版 Prompt
- 没有引用 `src/prompts/batch_extraction.py` 中的完整版 `BATCH_EXTRACTION_PROMPT_V1`

**修复代码**:
```python
# 修复前
BATCH_EXTRACTION_PROMPT = """简化版..."""
content = BATCH_EXTRACTION_PROMPT.format(...)

# 修复后
from src.prompts.batch_extraction import BATCH_EXTRACTION_PROMPT_V1
content = BATCH_EXTRACTION_PROMPT_V1.format(...)
```

**提交记录**: `cb30ea6` - fix: use correct prompt version in batch processor

---

## ✅ 总结

**新文件**: `05_input_new_prompt.jsonl`（1.5 MB）

**包含所有特性**:
- ✅ 中国作者识别规则
- ✅ 地址翻译（英文 + 中文）
- ✅ 多单位换行格式
- ✅ 复姓支持
- ✅ 详细示例
- ✅ all_authors_info_cn 字段

**下一步**: 提交新批处理任务，验证效果
