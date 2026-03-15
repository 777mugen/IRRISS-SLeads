# 智谱网页阅读 API 并发限制分析

## API 信息

**端点**: `POST https://open.bigmodel.cn/api/paas/v4/reader`

**功能**: 读取指定 URL 的网页内容，返回 markdown 或 text 格式

---

## 官方文档说明

根据智谱官方文档（https://docs.bigmodel.cn/api-reference/工具-api/网页阅读）：

### 请求参数

```python
{
  "url": "https://doi.org/10.1234/example",
  "return_format": "markdown",  # markdown 或 text
  "retain_images": true,
  "with_links_summary": true,
  "timeout": 20  # 超时时间，默认 20 秒
}
```

### 响应格式

```json
{
  "reader_result": {
    "content": "...",        # 网页内容
    "title": "...",          # 标题
    "source_url": "...",     # 原始 URL
    "links": [...]           # 链接摘要
  }
}
```

---

## 并发限制

### 官方文档中的限制

**未找到明确的并发限制说明**，但根据 API 设计和常见实践：

1. **超时限制**: `timeout` 参数默认 20 秒，最大建议不超过 60 秒
2. **速率限制**: 通常为 **30-60 次/分钟**（需要验证）
3. **并发限制**: 通常为 **5-10 个并发请求**（需要验证）

---

## 实际测试建议

由于官方文档未明确说明并发限制，建议：

### 保守策略（推荐）
- **并发数**: 3-5 个
- **请求间隔**: 1-2 秒
- **预计速度**: 120-180 篇/小时

### 激进策略（测试后使用）
- **并发数**: 10 个
- **请求间隔**: 0.5 秒
- **预计速度**: 360-480 篇/小时

---

## 实施方案

### 两步流程

```python
# 步骤 1: 网页阅读（串行或并发）
content = await zhipu_reader.read(doi_url)

# 步骤 2: 结构化输出（批量处理）
authors = await zhipu_batch.extract(content)
```

### 并发控制

```python
import asyncio
from asyncio import Semaphore

# 限制并发数
semaphore = Semaphore(5)  # 5 个并发

async def process_doi(doi):
    async with semaphore:
        # 步骤 1: 网页阅读
        content = await reader.read(f"https://doi.org/{doi}")
        
        # 保存到数据库
        await save_content(doi, content)
```

---

## 成本估算

### 网页阅读 API
- **费用**: 约 0.001 元/次（根据智谱定价）
- **1000 篇**: 约 1 元

### 结构化输出（批量）
- **费用**: 约 0.05 元/篇
- **1000 篇**: 约 50 元

### 总成本（网页阅读 + 结构化输出）
- **1000 篇**: 约 51 元
- **在预算范围内**（50-100 元）

---

## 推荐配置

**基于保守策略**：
- **并发数**: 5
- **请求间隔**: 1 秒
- **预计速度**: 150 篇/小时
- **1000 篇耗时**: ~6.7 小时

**配置**:
```python
CONCURRENT_REQUESTS = 5
REQUEST_DELAY = 1.0  # 秒
BATCH_SIZE = 100  # 每 100 篇批量处理
```

---

## 待确认

需要实际测试验证：
1. 智谱网页阅读 API 的实际并发限制
2. 是否会返回 429 错误（Too Many Requests）
3. 最佳并发数配置

建议先用 10 篇文章测试，观察是否有速率限制。
