---
date: 2026-03-13
topic: data-sync-strategy
---

# 数据同步策略：raw_markdown 与 paper_leads

## What We're Building

优化批处理流程，确保 `raw_markdown`（原始数据）和 `paper_leads`（业务数据）两个表的数据一致性。

**核心问题**: 当前批处理任务只更新字段，没有创建 paper_leads 记录，导致两个表数据不对应。

**解决方案**: 在智谱提取完成时，检查 paper_leads 是否存在，不存在则创建（包含所有必填字段）。

---

## Why This Approach

### 方案对比

#### ❌ 方案 2: 提前创建 paper_leads
- **问题**: paper_leads 有 8 个必填字段（title, published_at, article_url, source, name, address, phone, email）
- **冲突**: 提前创建会违反数据库约束
- **风险**: 智谱提取失败会留下空记录（脏数据）

#### ✅ 方案 1 + 优化: 延迟创建 paper_leads
- **优点**:
  - 符合数据库约束（创建时有所有必填字段）
  - 容错性好（提取失败不影响 paper_leads）
  - 状态清晰（raw_markdown 负责跟踪处理流程）
  - 支持重试（可根据 status 重新处理失败任务）

---

## Key Decisions

### 决策 1: 延迟创建 paper_leads
- **时机**: 智谱提取完成时
- **逻辑**: 检查 paper_leads 是否存在（通过 doi），不存在则创建
- **字段**: 包含所有必填字段（从提取结果获取）

### 决策 2: 状态跟踪在 raw_markdown
- **字段**: processing_status（pending/processing/completed/failed）
- **作用**: 跟踪处理流程，支持重试

### 决策 3: 错误处理
- **提取失败**: 更新 raw_markdown.status = 'failed'，不创建 paper_leads
- **记录错误**: raw_markdown.error_message 存储错误信息

---

## 优化后的流程

```
1. 查 DOI → 创建 raw_markdown (status=pending)
2. 爬 raw 数据 → 更新 raw_markdown.markdown_content
3. 送智谱提取 → 更新 raw_markdown (status=processing, batch_id)
4. 提取完成 → 
   - 检查 paper_leads 是否存在 (通过 doi)
   - 不存在 → 创建 paper_leads (包含所有必填字段)
   - 已存在 → 更新 paper_leads
   - 更新 raw_markdown (status=completed)
5. 提取失败 → 
   - 更新 raw_markdown (status=failed, error_message)
   - 不创建 paper_leads
```

---

## Open Questions

- [x] 如何处理必填字段约束？→ 延迟创建，创建时包含所有必填字段
- [ ] 如何处理重复提取？→ 通过 doi 检查，已存在则更新
- [ ] 如何处理部分失败？→ 标记 failed，不创建 paper_leads，支持重试

---

## Next Steps

→ `/ce:plan` for implementation details

### 实现任务
1. 修改 `scripts/process_batch_results.py`
   - 添加 paper_leads 创建逻辑（检查 doi 是否存在）
   - 包含所有必填字段
2. 更新错误处理
   - 提取失败时不创建 paper_leads
   - 记录错误信息到 raw_markdown.error_message
3. 测试流程
   - 使用现有批处理结果测试
   - 验证 paper_leads 创建成功
   - 验证字段完整性
