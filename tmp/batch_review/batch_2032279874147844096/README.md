# 批处理任务审查 - batch_2032279874147844096

**批次 ID**: `batch_2032279874147844096`  
**提交时间**: 2026-03-13 10:17  
**完成时间**: 2026-03-13 10:54  
**处理时长**: 37 分钟  
**成功率**: 100% (20/20)

---

## 📂 文件说明

| 文件 | 说明 | 格式 |
|------|------|------|
| `01_input.jsonl` | 输入文件（发送给智谱 API 的请求） | JSONL（每行一个 JSON 对象） |
| `02_output.jsonl` | 输出文件（智谱 API 返回的结果） | JSONL（每行一个 JSON 对象） |
| `README.md` | 本说明文件 | Markdown |

---

## 📊 任务统计

### 输入统计
- **论文数量**: 20 篇
- **数据来源**: PubMed（4 个关键词组合）
- **预筛选**: 单位地址包含中国关键词（China/城市名）

### 输出统计
- **总成功**: 20/20 (100%)
- **提取完整**: 11/20 (55%)
- **部分提取**: 9/20 (45%) - 部分字段缺失

---

## 🔍 输入文件格式说明 (01_input.jsonl)

**每行结构**:
```json
{
  "custom_id": "doi_10_1021_acs_jmedchem_5c03498",  // 自定义 ID（用于匹配输入输出）
  "method": "POST",                                  // HTTP 方法
  "url": "/v4/chat/completions",                    // API 端点
  "body": {                                          // 请求体
    "model": "glm-4-plus",                           // 模型名称
    "messages": [                                    // 对话消息
      {
        "role": "system",
        "content": "你是一个专业的学术论文信息提取助手..."
      },
      {
        "role": "user",
        "content": "从以下论文内容中提取信息...\n\n论文内容：\n[Markdown 内容]"
      }
    ],
    "max_tokens": 4096  // 最大输出 token 数
  }
}
```

**关键字段**:
- `custom_id`: DOI 转换而来（用于匹配输入输出）
- `model`: 使用 GLM-4-Plus 模型
- `messages[1].content`: 包含完整的 Prompt + 论文 Markdown 内容
- `max_tokens`: 4096（足够输出结构化 JSON）

---

## 🔍 输出文件格式说明 (02_output.jsonl)

**每行结构**:
```json
{
  "id": "1773369622_4457bc1e5f314ade98e613d2039362f6",  // 智谱生成的 ID
  "custom_id": "doi_10_1021_acs_jmedchem_5c03498",      // 与输入匹配的 ID
  "response": {                                          // 响应体
    "status_code": 200,                                  // HTTP 状态码
    "body": {                                            // 响应内容
      "id": "chatcmpl-xxx",
      "choices": [
        {
          "index": 0,
          "message": {
            "role": "assistant",
            "content": "{\n  \"title\": \"Near-Infrared II...\",\n  ...}"
          }
        }
      ]
    }
  },
  "error": null  // 错误信息（如果有）
}
```

**关键字段**:
- `custom_id`: 与输入文件的 `custom_id` 一一对应
- `response.status_code`: 200 = 成功
- `response.body.choices[0].message.content`: LLM 返回的 JSON 字符串

---

## 📝 提取结果示例

### 成功案例 1（完整提取）

**DOI**: `10.7150/thno.124789`  
**标题**: CEBPB-high dormant tumor cells drive immune evasion via S100...

**提取结果**:
```json
{
  "title": "CEBPB-high dormant tumor cells drive immune evasion via S100...",
  "published_at": "2024-03-15",
  "corresponding_author": {
    "name": "Yong Gao",
    "email": "drgaoyong@tongji.edu.cn",
    "phone": null,
    "institution": "Department of Oncology, Shanghai East Hospital, Tongji University School of Medicine",
    "address": "Department of Oncology, Shanghai East Hospital, Tongji University School of Medicine, 150 Jimo Road, Pudong District, Shanghai, 200120, China.",
    "address_cn": null  // ⚠️ 中文字段缺失
  },
  "all_authors_info": "...",
  "all_authors_info_cn": "..."
}
```

**状态**: ✅ 成功提取，但 `address_cn` 缺失

---

### 成功案例 2（部分提取）

**DOI**: `10.21037/tcr-2025-aw-2287`  
**标题**: Enhanced CT-based deep learning radiomics...

**提取结果**:
```json
{
  "title": "Enhanced CT-based deep learning radiomics and biological correlates...",
  "published_at": null,
  "corresponding_author": {
    "name": null,
    "email": null,
    "phone": null,
    "institution": null,
    "address": null,
    "address_cn": null
  },
  "all_authors_info": null,
  "all_authors_info_cn": null
}
```

**状态**: ⚠️ 标题提取成功，但作者信息全部缺失

---

## ⚠️ 发现的问题

### 1. 地址中文字段全部缺失

**问题**: 所有论文的 `address_cn` 都是 `null`

**原因分析**:
- Prompt 要求："address_cn: 中文翻译"
- LLM 没有理解或没有执行翻译要求

**解决方案**:
```python
# 优化 Prompt 示例
"address": "¹Department of Cardiology, West China Hospital, Chengdu 610041, China",
"address_cn": "¹四川大学华西医院心内科，成都 610041，中国"
```

---

### 2. 部分论文提取失败（9/20）

**问题**: 通讯作者信息全部为 `null`

**可能原因**:
- 论文格式特殊（如 PDF 转换质量差）
- 通讯作者信息位置不标准
- Jina Reader 获取的 Markdown 内容不完整

**示例**:
```
DOI: 10.3748/wjg.v32.i9.115259
标题: Azure WAF...  // ⬅️ 被反爬虫拦截
通讯作者: null
```

---

### 3. 非中国作者被提取

**问题**: 1 篇德国作者论文被提取

**DOI**: `10.1007/s43630-026-00863-7`  
**通讯作者**: Linglin Zhang（德国慕尼黑大学）  
**地址**: Laser-Forschungslabor, LIFE Center, University Hospital, Ludwig-Maximilian University, 82152, Planegg, Germany

**原因**:
- 预筛选只判断单位地址（包含关键词）
- 没有判断姓名是否是中国拼音

**解决方案**:
- LLM 提取时应根据姓名 + 地址组合判断
- 如果姓名是中文拼音 + 地址是德国 → 不应作为中国作者

---

## 🎯 提取字段统计

| 字段 | 成功数 | 成功率 | 说明 |
|------|--------|--------|------|
| `title` | 20/20 | 100% | 标题全部提取成功 |
| `published_at` | 18/20 | 90% | 2 篇为 null |
| `corresponding_author.name` | 11/20 | 55% | 9 篇缺失 |
| `corresponding_author.email` | 11/20 | 55% | 9 篇缺失 |
| `corresponding_author.phone` | 0/20 | 0% | 全部缺失（正常现象） |
| `corresponding_author.institution` | 11/20 | 55% | 9 篇缺失 |
| `corresponding_author.address` | 8/20 | 40% | 12 篇缺失 |
| `corresponding_author.address_cn` | 0/20 | 0% | **全部缺失（需优化 Prompt）** |
| `all_authors_info` | 11/20 | 55% | 9 篇缺失 |
| `all_authors_info_cn` | 0/20 | 0% | **全部缺失（需优化 Prompt）** |

---

## 🔧 改进建议

### 1. 优化 Prompt - 强制要求中文翻译

**当前 Prompt**:
```
address_cn: 通讯作者的单位地址（中文翻译，多单位换行）
```

**优化后**:
```
address_cn: **必须翻译成中文**，格式：
¹科室中文 → 机构中文 → 城市中文 → 邮编 → 国家中文

示例：
输入: "Department of Oncology, Fudan University, Shanghai 200032, China"
输出: "¹复旦大学肿瘤医院肿瘤科，上海 200032，中国"
```

---

### 2. 增加数据验证逻辑

**建议代码**:
```python
def validate_extraction(data):
    """验证提取结果"""
    errors = []
    
    # 检查必要字段
    if not data.get('corresponding_author', {}).get('name'):
        errors.append('通讯作者姓名缺失')
    
    # 检查地址中文字段
    if not data.get('corresponding_author', {}).get('address_cn'):
        errors.append('地址中文翻译缺失')
    
    # 检查中国作者判断
    address = data.get('corresponding_author', {}).get('address', '')
    name = data.get('corresponding_author', {}).get('name', '')
    
    if 'China' in address or '中国' in address:
        if not is_chinese_name(name):
            errors.append(f'非中国作者被提取: {name}')
    
    return errors
```

---

### 3. 增加重试机制

**建议**:
- 如果 `address_cn` 缺失 → 单独调用 API 补全
- 如果通讯作者缺失 → 标记为 "需人工审核"

---

## 📋 查看数据方式

### 方式 1: 直接查看 JSONL 文件

```bash
# 查看输入文件（第 1 行）
head -n 1 01_input.jsonl | python -m json.tool

# 查看输出文件（第 1 行）
head -n 1 02_output.jsonl | python -m json.tool
```

### 方式 2: 查询数据库

```sql
SELECT 
    doi,
    title,
    name AS corresponding_author,
    institution,
    address,
    address_cn
FROM paper_leads
WHERE batch_id = 'batch_2032279874147844096'
ORDER BY created_at DESC;
```

---

## 📊 批处理工作流

```
1. 搜索论文（PubMed API）
   ↓
2. 预筛选（单位地址包含 China）
   ↓
3. 获取 Markdown（Jina Reader）
   ↓
4. 创建批处理文件（01_input.jsonl）
   ↓
5. 上传到智谱 API
   ↓
6. 提交批处理任务
   ↓
7. 等待处理（37 分钟）
   ↓
8. 下载结果（02_output.jsonl）
   ↓
9. 解析 JSON + 更新数据库
   ↓
10. 完成 ✅
```

---

## 🎓 学习要点

### 1. JSONL 格式
- 每行一个独立的 JSON 对象
- 适合大规模数据处理
- 易于并行处理

### 2. 批处理 API
- 优势: 高吞吐、低成本
- 劣势: 非实时、需要轮询
- 适用场景: 大批量数据处理

### 3. Prompt Engineering
- 清晰的示例比描述更重要
- 必须字段用 **粗体** 强调
- 提供多个真实示例

---

## 📞 联系方式

如有问题，请联系：
- **开发者**: IRRISS Team
- **Feishu**: ou_267c16d0bbf426921ce84255b6cfd1f9
- **批次 ID**: batch_2032279874147844096

---

**生成时间**: 2026-03-13 11:00  
**文档版本**: v1.0
