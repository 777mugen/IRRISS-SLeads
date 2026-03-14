# Brainstorm: 优化元数据提取（Token 消耗 vs 准确性）

**日期**: 2026-03-14
**决策人**: 董胜豪

---

## 📋 问题背景

### 当前痛点

1. **Token 消耗高**
   - 当前方案：完整论文内容（80K+ 字符）
   - 预估 Token：~20,000 tokens/论文
   - 100 篇论文 = 200 万 tokens

2. **模型注意力问题**
   - 无效信息（Methodology, Results, Discussion）干扰
   - 导致提取准确性降低
   - 作者信息在第一页，后面的内容是噪音

3. **Prompt 过长**
   - 当前 Prompt v2：~8KB
   - 规则详细，但可能过度约束
   - 模型需要理解大量规则

---

## 🎯 目标

### 主要目标

**提高准确性** > 降低 Token 消耗

### 原则（已记录到 `docs/PRINCIPLES.md`）

1. ✅ **准确性优先**：不是为了节省 token，而是避免注意力问题
2. ✅ **迭代优化循环**：爬取 → 检查 → 优化 → 总结 → 优化
3. ✅ **自主检查和修复**：不接受人工修正

---

## 💡 方案探索

### 方案 1：精准截断 + 结构化 Prompt（推荐）⭐

#### 截断策略

**原则**：基于论文结构，不基于固定字符数

**实现**：
```python
def extract_metadata_section(content: str) -> str:
    """提取元数据部分（标题、作者、机构、摘要等）"""
    # 1. 按段落分割
    paragraphs = content.split('\n\n')
    
    # 2. 找到学术内容开始的位置
    stop_keywords = [
        'Introduction', 'Methods', 'Methodology',
        'Background', 'Results', 'Discussion'
    ]
    
    metadata_paragraphs = []
    for p in paragraphs:
        # 检测章节标题
        # 格式 1: "Introduction Other Section" (AME 出版社)
        # 格式 2: "# Introduction" 或 "## Introduction"
        if any(f"{kw} Other Section" in p for kw in stop_keywords):
            break
        if any(p.startswith(f"# {kw}") or p.startswith(f"## {kw}") for kw in stop_keywords):
            break
        
        metadata_paragraphs.append(p)
    
    return '\n\n'.join(metadata_paragraphs)
```

#### Prompt 策略

**长度**：中等（600-800 字）

**保留内容**：
- ✅ 核心规则（作者符号 #, †, *）
- ✅ 通讯作者识别规则（优先级）
- ✅ 中国作者识别规则（姓名 + 地址）
- ✅ 一个完整示例（带符号和地址）
- ✅ JSON 格式定义

**删除内容**：
- ❌ 详细的脚注说明（让模型自己理解）
- ❌ 多个示例（只需要一个）
- ❌ 过长的背景解释

#### 优点

- ✅ 平衡 token 消耗和准确性
- ✅ 基于论文结构，不会丢失信息
- ✅ Prompt 足够清晰，不会过度约束

#### 缺点

- ⚠️ 需要实现论文结构识别
- ⚠️ 不同期刊格式可能不同

#### Token 消耗估算

- 输入：5K-10K（元数据部分）
- Prompt：1K
- **总计：6K-11K**（比当前 80K 减少 **85%**）

---

### 方案 2：固定截断 + 极简 Prompt

#### 截断策略

**实现**：
```python
def extract_front_section(content: str) -> str:
    """提取前 3000 字符 + 正则提取关键词段落"""
    # 1. 固定截断
    front = content[:3000]
    
    # 2. 正则提取关键词段落
    keywords = ['Affiliation', 'Address', 'Email', 'Department', 'Correspondence']
    keyword_paragraphs = []
    
    for line in content.split('\n'):
        if any(kw in line for kw in keywords):
            keyword_paragraphs.append(line)
    
    return front + '\n\n' + '\n'.join(keyword_paragraphs)
```

#### Prompt 策略

**长度**：极简（100-200 字）

#### 优点

- ✅ Token 消耗最低
- ✅ 实现简单
- ✅ 让模型自己理解

#### 缺点

- ❌ 可能丢失信息（固定截断）
- ❌ Prompt 太短，可能不够准确
- ❌ 模型可能"幻觉"（编造信息）

#### Token 消耗估算

- 输入：3K-5K
- Prompt：0.2K
- **总计：3.2K-5.2K**（减少 **93%**）

---

### 方案 3：两阶段处理（最准确但最复杂）

#### 阶段 1：正则提取

```python
def extract_by_regex(content: str) -> dict:
    """用正则提取元数据"""
    # 提取标题、作者、邮箱、机构
    ...
```

#### 阶段 2：LLM 验证和补全

```python
# 阶段 1 结果 + 原文前 2000 字符
# LLM 验证并补全
```

#### 优点

- ✅ 最准确（两阶段验证）
- ✅ Token 消耗可控

#### 缺点

- ❌ 实现最复杂
- ❌ 需要维护正则规则
- ❌ 不同期刊格式需要不同正则

#### Token 消耗估算

- 阶段 1：0（正则）
- 阶段 2 输入：2K-3K
- Prompt：0.8K
- **总计：2.8K-3.8K**（减少 **95%**）

---

## 🎯 推荐方案

**方案 1：精准截断 + 结构化 Prompt** ⭐

### 推荐理由

1. **平衡性最好**：在 token 消耗和准确性之间找到最佳平衡
2. **基于结构**：不会丢失信息（不像固定截断）
3. **实现简单**：只需要识别段落结构，不需要复杂的正则
4. **Prompt 清晰**：中等长度的 Prompt 既能指导模型，又不会过度约束

### 对于关键问题的答案

#### 1. 截断标准

**建议**：基于论文结构，而不是固定字符数

**原因**：
- ✅ 不同期刊格式差异大
- ✅ 基于结构不会丢失信息
- ✅ 可以通过识别关键词来定位

**实现**：
```python
stop_keywords = ['Introduction', 'Methods', 'Background', 'Results']
```

#### 2. Prompt 长度

**建议**：中等长度（500-800 字），保留关键规则和示例

**原因**：
- ✅ 太短的 Prompt 可能导致模型"幻觉"
- ✅ 太长的 Prompt 可能过度约束
- ✅ 中等长度最平衡

**保留内容**：
- ✅ 作者符号规则（#, †, *）
- ✅ 通讯作者识别规则
- ✅ 一个完整示例
- ❌ 详细的脚注说明
- ❌ 多个示例

---

## 📊 实施计划

### 阶段 1：实现（已完成）✅

1. ✅ 实现截断函数（`src/processors/content_truncator.py`）
2. ✅ 创建新 Prompt v3（`docs/Batch Prompt v3 (Simplified).md`）
3. ✅ 创建 A/B 测试框架（`scripts/ab_test.py`）
4. ✅ 测试截断功能（90.2% 减少）

### 阶段 2：A/B 测试

**测试集**：
- 10 篇论文（不同期刊）
- 包含 AME, Frontiers, Nature 等

**对比指标**：
1. Token 消耗
2. 提取准确性（作者姓名、邮箱、地址）
3. 处理速度

### 阶段 3：检查和定位

**流程**：
1. 浏览器打开每篇论文
2. 对比原始内容 vs 提取结果
3. 统计准确率（字段级别）
4. 定位问题环节

### 阶段 4：优化和迭代

**流程**：
1. 根据问题类型优化
2. 重新测试
3. 回到阶段 3

### 阶段 5：总结和文档

**流程**：
1. 记录每种期刊的特点
2. 总结最佳实践
3. 更新文档

---

## 🧪 测试结果（初步）

### 测试论文

**DOI**: 10.21037/tcr-2025-1389

### 截断效果

| 指标 | v1（当前） | v2（新） | 减少 |
|------|----------|---------|------|
| **输入长度** | 81,186 字符 | 7,939 字符 | **90.2%** ⭐ |
| **预估 Token** | ~20,000 | ~2,000 | **90%** ⭐ |

### 关键信息保留

- ✅ 作者全名: 保留（Zhilan Huang, Wei Xie）
- ✅ 机构地址: 保留（完整）
- ✅ 通讯作者: 保留（Wei Xie）
- ✅ 邮箱: 保留（xiew0703@163.com）
- ✅ 共同第一作者标注: 保留（#）
- ✅ 发表日期: 保留（Feb 12, 2026）

### 学术内容去除

- ✅ Introduction: 已去除
- ✅ Discussion: 已去除

---

## 🔑 关键决策

| 决策 | 理由 | 决策人 |
|------|------|--------|
| 使用方案 1 | 平衡性最好 | 基于分析 |
| 基于结构截断 | 不会丢失信息 | 基于分析 |
| 中等长度 Prompt | 避免幻觉和过度约束 | 基于经验 |
| 创建新分支 | 保留当前版本进行 A/B 测试 | 董胜豪 |

---

## 📂 相关文档

- `docs/PRINCIPLES.md` - 项目核心原则
- `docs/Batch Prompt v2.md` - 当前版本 Prompt
- `docs/Batch Prompt v3 (Simplified).md` - 新版本 Prompt
- `src/processors/content_truncator.py` - 截断函数实现
- `scripts/ab_test.py` - A/B 测试框架
- `scripts/test_truncation.py` - 截断功能测试

---

## 📋 Open Questions

1. **期刊格式差异**：是否需要针对不同期刊（AME, Frontiers, Nature）使用不同的截断规则？
   - **解决方案**：先测试，根据结果调整

2. **准确性验证**：如何自动验证提取结果的准确性？
   - **解决方案**：使用浏览器打开原始论文，对比提取结果

3. **边界情况**：如果作者信息不在第一页怎么办？
   - **解决方案**：先测试，根据结果调整截断策略

---

## 🚀 下一步

1. **运行 A/B 测试**：使用 10 篇论文对比 v1 和 v2
2. **浏览器验证**：打开原始论文，检查提取结果
3. **优化迭代**：根据结果调整截断规则和 Prompt
4. **合并分支**：如果 v2 效果更好，合并到 main

---

**Git 分支**: `feature/metadata-extraction-v2`
**Git Commit**: bcbdf09
