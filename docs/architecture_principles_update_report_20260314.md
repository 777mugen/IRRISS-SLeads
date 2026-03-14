# 架构原则更新报告

**日期**: 2026-03-14
**决策人**: 董胜豪
**Git Commit**: e1dd442

---

## ✅ 完成的工作

### 1. 架构原则确立

**核心原则**:
- ✅ **保留所有原始数据**（图片、链接、完整HTML结构）
- ✅ **提取和处理逻辑放在后续环节**（智谱批处理、解析器）
- ✅ **实现最大的灵活性**

**文档**:
- ✅ `docs/ARCHITECTURE_PRINCIPLES.md` - 架构原则文档
- ✅ `docs/jina_api_parameters.md` - API 参数文档（已更新）
- ✅ `src/crawlers/jina_client.py` - 代码实现（已更新）

---

### 2. Jina Reader API 参数配置

**更新前**（旧配置）:
```python
'X-Retain-Links': 'none',  # ❌ 去除所有链接
'X-Retain-Images': 'none',  # ❌ 去除所有图片
```

**更新后**（新配置）:
```python
'X-Retain-Links': 'all',    # ✅ 保留所有链接（图片链接、邮箱链接等）
'X-Retain-Images': 'all',   # ✅ 保留所有图片
```

**其他优化**:
```python
'X-Respond-Timing': 'network-idle',  # ✅ 等待网络完全空闲
'X-Timeout': '90',                    # ✅ 增加超时时间（90秒）
'X-Token-Budget': '100000',           # ✅ 增加 token 预算
```

---

### 3. 验证测试

**测试论文**: DOI: 10.21037/tcr-2025-1389

**关键信息验证**:
- ✅ 作者全名: Zhilan Huang, Tingyi Xie, Wei Xie
- ✅ 机构地址: 
  - 1 The Fourth Clinical Medical College of Guangzhou University of Chinese Medicine, Shenzhen, China
  - 2 Department of Respiratory Medicine, Shenzhen Traditional Chinese Medicine Hospital, Shenzhen, China
- ✅ 通讯作者: Wei Xie
- ✅ 邮箱: xiew0703@163.com
- ✅ 共同第一作者标注: # (contributed equally)
- ✅ 图片链接: 15 个
- ✅ 所有链接: 287 个（包括图片链接）

**总长度**: 81,186 字符

**测试脚本**: `scripts/test_jina_raw_data.py`

---

### 4. 数据管道架构

```
┌─────────────────┐
│  Jina Reader    │ → 保留所有原始数据（图片、链接、完整HTML结构）
│  (Raw Data)     │
└─────────────────┘
        ↓
┌─────────────────┐
│  raw_markdown   │ → 存储原始 Markdown（包含所有信息）
│  (Storage)      │
└─────────────────┘
        ↓
┌─────────────────┐
│  智谱批处理      │ → 提取结构化信息（标题、作者、地址等）
│  (Extraction)   │
└─────────────────┘
        ↓
┌─────────────────┐
│  paper_leads    │ → 存储结构化数据（提取后的信息）
│  (Storage)      │
└─────────────────┘
        ↓
┌─────────────────┐
│  评分/导出/应用  │ → 业务逻辑（评分、导出CSV、Feishu通知）
│  (Business)     │
└─────────────────┘
```

---

### 5. 决策记录

| 日期 | 决策 | 原因 | 决策人 |
|------|------|------|--------|
| 2026-03-14 | 保留所有原始数据（图片、链接） | 实现最大的灵活性 | 董胜豪 |
| 2026-03-14 | 提取和处理逻辑放在后续环节 | 数据清洗在应用层更灵活 | 董胜豪 |

---

## 📊 对比分析

### 之前的问题

**问题论文**: DOI: 10.21037/tcr-2025-1389

**用户反馈**:
1. ❌ 作者姓名: 原文 "Zhilan Huang", CSV "Huang Z" (缩写)
2. ❌ 地址: 原文有地址, CSV 为空
3. ❌ 通讯作者: 原文 "Wei Xie", CSV 是 "Huang Z" (错误)
4. ❌ 其他作者字段: 全部缺失

**根本原因**: Jina API 参数配置过于激进，删除了关键信息

---

### 修复后

**测试结果**:
- ✅ 作者全名: 完整提取
- ✅ 机构地址: 完整提取
- ✅ 通讯作者: 正确识别
- ✅ 邮箱: 完整提取
- ✅ 图片链接: 保留（15 个）
- ✅ 所有链接: 保留（287 个）

**架构优势**:
- ✅ 原始数据完整保留
- ✅ 后续处理灵活调整
- ✅ 不会丢失任何信息

---

## 📝 下一步

### 1. 重新爬取论文

**建议**: 对已爬取的论文重新爬取（特别是 AME 出版社的论文）

**脚本**: 
```python
# 重新爬取 DOI: 10.21037/tcr-2025-1389
python scripts/test_jina_raw_data.py
```

---

### 2. 更新智谱批处理 Prompt

**需要在 Prompt 中明确**:
- 从 Markdown 文本中提取作者姓名（忽略图片链接）
- 从 Markdown 文本中提取邮箱（忽略 `mailto:` 链接）
- 从 Markdown 文本中提取地址（忽略图片）
- 识别通讯作者标注（*、#、†等符号）
- 翻译机构地址为中文

**文件**: `docs/Batch Prompt v2.md`

---

### 3. 测试更多论文

**建议**: 测试不同出版社的论文，验证稳定性

**出版社列表**:
- ✅ AME 出版社 (tcr.amegroups.org)
- Frontiers (frontiersin.org)
- Nature (nature.com)
- Science (science.org)
- PLoS (plos.org)

---

## 🔗 相关文档

- `docs/ARCHITECTURE_PRINCIPLES.md` - 架构原则文档
- `docs/jina_api_parameters.md` - Jina API 参数配置
- `docs/Batch Prompt v2.md` - 智谱批处理 Prompt
- `src/crawlers/jina_client.py` - Jina Reader API 实现
- `src/processors/batch_result_parser.py` - 数据清洗逻辑
- `memory/2026-03-13.md` - 工作记录

---

## ✅ 总结

**核心成就**:
1. ✅ 确立了"原始数据优先"的架构原则
2. ✅ 更新了 Jina API 参数配置（保留所有原始数据）
3. ✅ 验证了新配置能够提取完整信息
4. ✅ 更新了项目文档

**Git 提交**: e1dd442

**下一步**: 重新爬取论文并更新智谱批处理 Prompt
