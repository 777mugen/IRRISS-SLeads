---
title: "Jina Reader API 参数优化配置"
created: 2026-03-13
modified: 2026-03-13
tags: [jina, api, optimization, batch-processing, prompt-v2]
component: jina-reader-api
problem_type: performance-optimization
---

# Jina Reader API 参数优化配置

## 问题概述

在集成 Jina Reader API 抓取学术论文时，遇到以下问题：

**症状**:
- 反爬虫拦截风险（3/5 论文被拦截）
- 图片和链接干扰内容
- 提取质量不稳定（33% 成功率）
- `address_cn` 字段全部缺失
- 电话字段提取失败
- 响应速度需优化

**受影响系统**:
- Jina Reader API（反爬虫、参数配置）
- 智谱批处理系统（JSONL 格式、Prompt 结构）
- LLM 提取模块（JSON 解析、字段提取）

---

## 根本原因

1. **Jina Reader 默认参数未优化**
   - 未设置 `X-Engine: browser` 导致反爬虫拦截
   - 未去除图片和链接，干扰内容提取
   - 默认 30 秒超时不够（学术论文加载慢）

2. **批处理 Prompt 未分离 system/user role**
   - JSONL 格式不符合智谱官方规范
   - 缺少 `temperature: 0.1` 参数

3. **提取 Prompt 不够详细**
   - 未明确 `address_cn` 翻译规则
   - 电话字段提取规则缺失
   - 缺少脚注、符号说明等细节

---

## 解决方案

### 1. Jina Reader API 参数优化

在 `JinaClient` 类中新增 `read_paper()` 方法，针对学术论文场景优化：

**关键优化参数**:
- `X-Engine: browser` - 模拟浏览器，减少反爬
- `X-Retain-Links: none` - 去除链接
- `X-Retain-Images: none` - 去除图片
- `X-Respond-Timing: resource-idle` - 平衡速度和完整性
- `X-Cache-Tolerance: 3600` - 利用缓存提升速度
- `X-Referer: https://doi.org/` - 模拟从 DOI 跳转
- `X-Remove-Selector` - 移除导航、广告、图片等干扰元素
- `X-Token-Budget: 50000` - 控制 token 消耗

**代码实现**:

```python
async def read_paper(self, doi_url: str) -> str:
    """
    读取学术论文 DOI 链接（优化版）
    
    特点:
    - 模拟浏览器减少反爬
    - 去除图片和链接
    - 利用缓存提升速度
    """
    reader_url = f"https://r.jina.ai/{doi_url}"
    
    headers = {
        'Authorization': f'Bearer {self.api_key}',
        'Accept': 'text/plain',
        'X-Respond-With': 'markdown',
        'X-Respond-Timing': 'resource-idle',
        'X-Timeout': '60',
        'X-Engine': 'browser',
        'X-Cache-Tolerance': '3600',
        'X-Remove-Selector': (
            'nav, aside, footer, .sidebar, '
            '.advertisement, .comments, '
            '.related-articles, .social-share, '
            'img, a img, figure'
        ),
        'X-Retain-Links': 'none',
        'X-Retain-Images': 'none',
        'X-With-Generated-Alt': 'false',
        'X-Locale': 'en-US',
        'X-Referer': 'https://doi.org/',
        'X-Token-Budget': '50000',
        'X-Robots-Txt': 'false'
    }
    
    response = await self._client.get(reader_url, headers=headers, timeout=65)
    response.raise_for_status()
    
    return response.text
```

### 2. 批处理 Prompt 更新到 v2

**文件**: `docs/Batch Prompt v2.md`

**关键改进**:
- 详细的作者符号规则（#、†、*）
- 脚注说明和降级处理
- 地址格式支持（斜杠、多机构）
- 完整的联系人识别规则
- 真实的示例输出

**动态注入**: `# 论文内容` → `{markdown_content}`

**代码实现**:

```python
# 双 role 结构（system + user）
request = {
    "custom_id": f"doi_{paper.doi.replace('/', '_')}",
    "method": "POST",
    "url": "/v4/chat/completions",
    "body": {
        "model": "glm-4-plus",
        "messages": [
            {
                "role": "system",
                "content": "你是一个专业的学术论文信息提取助手。严格按照规则提取，返回 JSON 格式。"
            },
            {
                "role": "user",
                "content": BATCH_EXTRACTION_PROMPT_V1.replace(
                    "{markdown_content}", 
                    paper.markdown_content
                )
            }
        ],
        "temperature": 0.1,
        "max_tokens": 4096
    }
}
```

**重要**: 使用 `.replace()` 而不是 `.format()`，避免 JSON 示例中的花括号导致 `KeyError`

---

## 实施步骤

### Step 1: 更新 JinaClient
- ✅ 新增 `read_paper()` 方法
- ✅ 配置 15 个优化参数

### Step 2: 更新批处理 Prompt
- ✅ 使用 `docs/Batch Prompt v2.md`
- ✅ 双 role 结构（system + user）
- ✅ 添加 `temperature: 0.1`

### Step 3: 创建新的批处理文件
- ✅ 文件：`09_input_prompt_v2.jsonl`
- ✅ 大小：1581.1 KB（20 篇论文）

### Step 4: 提交并推送
- ✅ Git commit: `e856372`
- ✅ 推送到 origin/main

---

## 测试结果

**批处理文件**: `tmp/batch_review/batch_2032279874147844096/09_input_prompt_v2.jsonl`

**格式验证**:
- ✅ 双 role 结构（system + user）
- ✅ 使用 Prompt v2
- ✅ 动态注入论文内容
- ✅ temperature: 0.1

---

## 效果对比

| 项目 | 优化前 | 优化后 |
|------|--------|--------|
| **反爬虫拦截** | 60% (3/5) | 预期 < 10% |
| **内容纯度** | 低（包含图片、链接） | 高（无图片、无链接） |
| **超时时间** | 30 秒 | 60 秒 |
| **缓存利用** | 无 | 1 小时 |
| **Prompt 结构** | 单 user role | 双 role（system + user） |
| **输出稳定性** | 一般 | temperature: 0.1 |

---

## 注意事项

1. **API Key 安全**: 使用环境变量或配置文件
2. **并发控制**: 付费用户建议 3-5 个并发
3. **错误处理**: 添加重试逻辑和详细日志
4. **缓存利用**: 学术论文不常变化，充分利用缓存
5. **Token 预算**: 监控消耗，避免超支

---

## 相关文档

- **实现计划**: `docs/plans/2026-03-13-jina-api-optimization.md`
- **参数说明**: `docs/jina_api_parameters.md`
- **Prompt v2**: `docs/Batch Prompt v2.md`
- **代码实现**: `src/crawlers/jina_client.py`
- **批处理代码**: `src/processors/batch_processor.py`

---

## 后续任务

- [ ] 提交新的批处理任务（使用 Prompt v2）
- [ ] 验证 address_cn 字段
- [ ] 验证中国作者识别准确性
- [ ] 对比新旧结果质量

---

## 参考资料

- Jina Reader API 文档: https://r.jina.ai/docs
- 智谱批处理 API 文档: https://docs.bigmodel.cn/cn/guide/tools/batch
- 付费用户配额说明: https://jina.ai/reader/pricing

---

**创建日期**: 2026-03-13  
**最后修改**: 2026-03-13  
**Git Commit**: e856372
