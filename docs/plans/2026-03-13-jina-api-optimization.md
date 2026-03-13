# Plan: Jina API 参数优化和批处理提交

**Created**: 2026-03-13 20:03
**Author**: OpenClaw Assistant
**Status**: Ready for Execution
**Related Memory**: `memory/2026-03-13.md`

---

## 📋 Objective

优化 Jina Reader API 参数配置，提升学术论文内容提取质量，并提交新的批处理任务。

---

## 🎯 Goals

1. **优化 Jina API 参数** - 减少反爬虫，提升速度，去除图片和链接
2. **更新代码实现** - 应用优化后的参数配置
3. **提交新批处理任务** - 使用正确的 JSONL 格式（双 role）
4. **验证提取质量** - 检查 address_cn、中国作者识别等字段

---

## 📊 Background

### Current State
- ✅ 已创建符合智谱官方格式的 JSONL 文件（`07_input_correct_format.jsonl`）
- ✅ 双 role 结构：`system`（身份）+ `user`（任务）
- ✅ 20 篇论文已获取
- ⚠️ 当前 Jina API 参数配置较简单，未充分利用官方 API 的优化参数

### User Requirements
- 去除图片和链接
- 减少反爬虫概率
- 提升速度
- 付费用户（有 API Key）

---

## 🔧 Technical Design

### 1. Jina API 参数优化

**Current Configuration**:
```python
headers = {
    "Authorization": f"Bearer {api_key}"
}
```

**Optimized Configuration**:
```python
headers = {
    'Authorization': f'Bearer {api_key}',
    'Accept': 'text/plain',
    'X-Respond-With': 'markdown',
    'X-Respond-Timing': 'resource-idle',
    'X-Timeout': '60',
    'X-Engine': 'browser',
    'X-Cache-Tolerance': '3600',
    'X-Remove-Selector': 'nav, aside, footer, .sidebar, .advertisement, .comments, .related-articles, .social-share, img, a img, figure',
    'X-Retain-Links': 'none',
    'X-Retain-Images': 'none',
    'X-With-Generated-Alt': 'false',
    'X-Locale': 'en-US',
    'X-Referer': 'https://doi.org/',
    'X-Token-Budget': '50000',
    'X-Robots-Txt': 'false'
}
```

**Key Improvements**:
1. `X-Engine: browser` - 模拟浏览器，减少反爬虫概率
2. `X-Retain-Links: none` - 去除链接（用户要求）
3. `X-Retain-Images: none` - 去除图片（用户要求）
4. `X-Respond-Timing: resource-idle` - 平衡速度和完整性
5. `X-Cache-Tolerance: 3600` - 利用缓存提升速度
6. `X-Referer: https://doi.org/` - 模拟从 DOI 跳转

### 2. Code Changes

**File: `src/crawlers/jina_client.py`**
- ✅ 新增 `read_paper()` 方法
- ✅ 使用优化后的参数配置

**File: `scripts/fetch_real_papers.py`**
- ✅ 更新为使用 `read_paper()` 方法

### 3. Batch Processing Task

**Input File**: `tmp/batch_review/batch_2032279874147844096/07_input_correct_format.jsonl`
**Format**: 符合智谱官方文档（双 role 结构）
**Papers**: 20 篇（100% 包含中国作者）

---

## 📝 Implementation Steps

### Step 1: Code Updates ✅ (已完成)
- [x] 更新 `src/crawlers/jina_client.py`
- [x] 更新 `scripts/fetch_real_papers.py`

### Step 2: Commit Changes
- [ ] Git add 修改的文件
- [ ] Git commit（包含详细说明）
- [ ] Git push

### Step 3: Submit Batch Task
- [ ] 上传 `07_input_correct_format.jsonl` 到智谱
- [ ] 创建批处理任务
- [ ] 记录 batch_id

### Step 4: Monitor and Validate
- [ ] 轮询批处理状态
- [ ] 下载结果文件
- [ ] 验证 address_cn 字段
- [ ] 验证中国作者识别准确性
- [ ] 对比新旧结果

### Step 5: Update Documentation
- [ ] 更新 memory/2026-03-13.md
- [ ] 更新 docs/jina_api_parameters.md
- [ ] 创建结果分析报告

---

## ⚠️ Risks & Mitigations

### Risk 1: Jina API 限流
- **Mitigation**: 并发控制（3 个），利用缓存，付费用户优先级

### Risk 2: 批处理任务失败
- **Mitigation**: 检查 JSONL 格式，验证文件大小，记录错误日志

### Risk 3: 提取质量不佳
- **Mitigation**: 对比新旧结果，调整 Prompt，增加示例

---

## 📊 Success Criteria

- [ ] Jina API 参数优化完成
- [ ] 代码更新并提交
- [ ] 批处理任务成功提交
- [ ] address_cn 字段正确生成（非 None）
- [ ] 中国作者识别准确率 > 80%
- [ ] 文档更新完成

---

## 🚀 Next Actions

1. **立即执行**: 提交代码更新（Git commit + push）
2. **提交批处理**: 上传 JSONL 文件并创建任务
3. **监控状态**: 等待批处理完成（约 30-40 分钟）
4. **验证结果**: 下载并分析结果文件

---

## 📎 Related Files

- `src/crawlers/jina_client.py` - Jina API 客户端
- `scripts/fetch_real_papers.py` - 论文获取脚本
- `tmp/batch_review/batch_2032279874147844096/07_input_correct_format.jsonl` - 批处理输入
- `docs/jina_api_parameters.md` - 参数说明文档
- `memory/2026-03-13.md` - 工作记录

---

## 🔗 References

- Jina Reader API 文档: https://r.jina.ai/docs#tag/crawl/paths/~1/get
- 智谱批处理 API 文档: https://docs.bigmodel.cn/cn/guide/tools/batch
- 前次批处理结果: `tmp/batch_review/batch_2032279874147844096/02_output.jsonl`

---

**Plan Status**: ✅ Ready for Execution
