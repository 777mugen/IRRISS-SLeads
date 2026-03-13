# JSONL 格式更新说明

**更新时间**: 2026-03-13 12:45  
**更新原因**: 符合智谱官方批处理 API 文档

---

## 📋 更新内容

### 旧格式 (05_input_new_prompt.jsonl)

```jsonl
{
  "custom_id": "doi_xxx",
  "method": "POST",
  "url": "/v4/chat/completions",
  "body": {
    "model": "glm-4-plus",
    "messages": [
      {
        "role": "user",
        "content": "提示词 + 论文内容（拼接在一起）"
      }
    ],
    "max_tokens": 4096
  }
}
```

**问题**:
- ❌ 只有 `user` role
- ❌ Prompt 和内容混在一起
- ❌ 不完全符合官方示例

---

### 新格式 (07_input_correct_format.jsonl) ✅

```jsonl
{
  "custom_id": "doi_10_21037_tcr-2025-aw-2287",
  "method": "POST",
  "url": "/v4/chat/completions",
  "body": {
    "model": "glm-4-plus",
    "messages": [
      {
        "role": "system",
        "content": "你是一个专业的学术论文信息提取助手。\n\n**🔴 严格遵守规则**：\n\n1. **绝对不要提取 References 部分的任何信息**\n2. **中国作者识别规则（姓名 + 地址组合判断）**\n3. **字段对应关系**（address、电话、邮箱对应通讯作者）\n4. **翻译要求**（address_cn 中文翻译）\n5. **作者信息合集格式**（all_authors_info + all_authors_info_cn）\n\n**如果某个字段找不到，设为 null**\n\n返回 JSON 格式，只返回 JSON，"
      },
      {
        "role": "user",
        "content": "从以下论文内容中提取信息，以 JSON 格式返回。\n\n**🔴 严格遵守规则**：\n\n1. **绝对不要提取 References 部分的任何信息**：\n   - References 中的作者姓名、单位、联系方式\n   - References 中的文章标题、DOI\n   - References 中的任何其他信息\n   - 只提取正文内容（References 之前的部分）\n\n...\n\n论文内容：\n[Markdown 内容]"
      }
    ],
    "max_tokens": 4096
  }
}
```

**优点**:
- ✅ **符合智谱官方文档格式**
- ✅ **System Role**: 固定规则（提示词核心）
- ✅ **User Role**: 动态内容（完整 Prompt + 论文 Markdown）
- ✅ **更清晰**: 规则和内容分离
- ✅ **更易维护**: 修改提示词只需改 system

---

## 🔍 对比官方示例

**智谱官方示例**:
```jsonl
{"custom_id": "request-1", "method": "POST", "url": "/v4/chat/completions", "body": {"model": "glm-4", "messages": [{"role": "system", "content": "你是一个专业的助理。"}, {"role": "user", "content": "请从以下文本中提取姓名和电话：\n\n张三的电话是123456，住在北京。"}]}}
```

**我们的新格式**:
```jsonl
{
  "custom_id": "doi_xxx",
  "method": "POST",
  "url": "/v4/chat/completions",
  "body": {
    "model": "glm-4-plus",
    "messages": [
      {"role": "system", "content": "你是一个专业的学术论文信息提取助手..."},
      {"role": "user", "content": "从以下论文内容中提取信息...\n\n论文内容：\n[Markdown]"}
    ],
    "max_tokens": 4096
  }
}
```

**对比结果**: ✅ **完全符合官方格式**

---

## 📊 文件对比

| 文件 | 大小 | 格式 | 说明 |
|------|------|------|------|
| 01_input.jsonl | 1.4 MB | 旧格式（简化 Prompt） | 实际使用的版本（缺少特性） |
| 05_input_new_prompt.jsonl | 1.5 MB | 旧格式（完整 Prompt） | Prompt + 内容在 user role |
| **07_input_correct_format.jsonl** | **1.5 MB** | **新格式（官方示例）** ✅ | **System + User 双 role** |

---

## ✅ 总结

**更新内容**:
- ✅ 按照**智谱官方文档**格式重新生成
- ✅ 添加 `system` role（固定规则）
- ✅ `user` role（完整 Prompt + 论文内容）
- ✅ 符合官方示例结构

**下一步**:
- 提交新的批处理任务
- 验证提取效果
- 对比新旧结果

---

**新文件已创建**: `tmp/batch_review/batch_2032279874147844096/07_input_correct_format.jsonl`
