# 数据质量分析报告

**日期**: 2026-03-14
**分析人**: AI 助理
**问题论文**: DOI: 10.21037/tcr-2025-1389

---

## 问题确认

用户反馈该论文的提取结果存在以下问题：

1. ❌ **作者姓名**: 原文 "Zhilan Huang", CSV "Huang Z" (缩写)
2. ❌ **地址**: 原文有地址, CSV 为空
3. ❌ **通讯作者**: 原文 "Wei Xie", CSV 是 "Huang Z" (错误)
4. ❌ **其他作者字段**: 全部缺失

---

## 根本原因

**Jina Reader API 参数配置问题** ❌

用户手动使用 Jina 提取的内容**包含完整信息**，我的 API 调用提取的内容**缺失关键信息**

### 对比验证

| 信息 | 用户手动提取 | 我的 API 提取 | 差异 |
|------|-------------|-------------|------|
| **作者全名** | ✅ Zhilan Huang, Tingyi Xie, Wei Xie... | ❌ 缺失 | **关键差异** |
| **机构地址** | ✅ 完整 | ❌ 缺失 | **关键差异** |
| **通讯作者** | ✅ Wei Xie (xiew0703@163.com) | ❌ 缺失 | **关键差异** |
| **标注符号** | ✅ # (共同第一作者) | ❌ 缺失 | **关键差异** |

---

## 问题参数

我的 `read_paper` 方法使用的参数：

```python
'X-Respond-Timing': 'resource-idle',  # ❌ 可能过早提取
'X-Remove-Selector': 'img, a img, figure',  # ❌ 可能误删作者信息
'X-Retain-Links': 'none',  # ❌ 去除所有链接
'X-Retain-Images': 'none',  # ❌ 去除所有图片
```

**问题**:
1. **X-Remove-Selector** 过于激进， 可能误删作者信息
2. **X-Retain-Links: 'none'** 去除了作者邮箱链接
3. **X-Respond-Timing: 'resource-idle'** 可能在页面完全加载前提取

---

## 解决方案

### **方案 A**: 调整 Jina API 参数** (推荐) ⭐

**新增方法**: `read_paper_v2`

**关键调整**:
```python
'X-Respond-Timing': 'network-idle',  # ✅ 等待网络完全空闲
'X-Timeout': '90',  # ✅ 增加超时时间
'X-Remove-Selector': (
    'nav, aside, footer, .sidebar, '
    '.advertisement, .comments, '
    '.related-articles, .social-share'
),  # ✅ 不删除 img, figure
'X-Retain-Links': 'all',  # ✅ 保留链接（作者邮箱等）
'X-Token-Budget': '80000',  # ✅ 增加 token 预算
```

---

### **方案 B**: 使用备用数据源

如果 Jina 仍无法修复:
1. **PubMed API** - 从 PubMed 获取作者信息
2. **CrossRef API** - 获取 DOI 元数据
3. **Unpaywall API** - 获取开放获取版本

---

## 验证结果

### 测试新方法

**测试 URL**: https://doi.org/10.21037/tcr-2025-1389

**提取结果**:
- ✅ **标题**: Construction and validation of a palmitoylation-related prognostic model...
- ✅ **作者全名**: Zhilan Huang 1#, Tingyi Xie 1#, Mingwen Tang 2, Anqi Su 1...
- ✅ **机构地址**: 
  - 1 The Fourth Clinical Medical College of Guangzhou University of Chinese Medicine, Shenzhen, China
  - 2 Department of Respiratory Medicine, Shenzhen Traditional Chinese Medicine Hospital, Shenzhen, China
- ✅ **通讯作者**: Wei Xie
- ✅ **邮箱**: xiew0703@163.com
- ✅ **共同第一作者标注**: # These authors contributed equally to this work

**结论**: 新的 `read_paper_v2` 方法成功提取完整信息 ✅

---

## 建议

1. **立即修复**: 使用新的 `read_paper_v2` 方法替换原来的 `read_paper`
2. **重新爬取**: 对已爬取的论文重新爬取（特别是AME出版社的论文）
3. **测试验证**: 对更多论文进行测试，验证稳定性
4. **文档更新**: 更新 `docs/jina_api_parameters.md`

---

## 下一步

**需要你确认**:
- [ ] 是否使用 `read_paper_v2` 替换 `read_paper`?
- [ ] 是否重新爬取已有论文?
- [ ] 是否测试更多论文验证稳定性?
