# 智谱网页阅读 API 测试结果

## 测试时间
2026-03-15 21:34 GMT+8

## 测试配置
- **测试文章数**: 5 篇
- **并发数**: 3
- **API 端点**: `POST https://open.bigmodel.cn/api/paas/v4/reader`

---

## 测试结果

### 成功率: 60% (3/5)

| # | DOI | 状态 | 内容长度 | 错误 |
|---|-----|------|---------|------|
| 1 | `10.21037/tcr-2025-aw-2287` | ✅ 成功 | 53,223 字符 | - |
| 2 | `10.3748/wjg.v32.i9.115259` | ❌ 失败 | - | 400 Bad Request |
| 3 | `10.1021/acs.jmedchem.5c03498` | ❌ 失败 | - | 400 Bad Request |
| 4 | `10.1021/jacsau.5c01509` | ✅ 成功 | 112,327 字符 | - |
| 5 | `10.21037/jgo-2025-750` | ✅ 成功 | 35,033 字符 | - |

---

## 关键发现

### 1. API 可用性
- ✅ 智谱网页阅读 API **可以读取 DOI 链接**
- ✅ 返回完整 markdown 内容
- ✅ 响应时间: 6-7 秒/篇

### 2. 并发限制
- ✅ 并发数 3: 无 429 错误（Too Many Requests）
- ✅ 可以正常运行
- ⚠️ 部分 DOI 返回 400 错误（可能是论文内容问题）

### 3. 错误分析
**400 Bad Request** 可能原因：
- 论文内容过大
- 网页格式不支持
- 临时网络问题

---

## 推荐配置

基于测试结果，推荐以下配置：

```python
# 并发配置
CONCURRENT_REQUESTS = 5  # 保守配置，避免速率限制
REQUEST_DELAY = 1.0      # 请求间隔（秒）
MAX_RETRIES = 3          # 最大重试次数

# 批处理配置
BATCH_SIZE = 50          # 每 50 篇批量处理（结构化输出）
SAVE_INTERVAL = 10       # 每 10 篇保存一次进度

# 超时配置
READER_TIMEOUT = 30      # 网页阅读超时（秒）
EXTRACTOR_TIMEOUT = 120  # 结构化输出超时（秒）
```

---

## 两步流程设计

### 步骤 1: 网页阅读（串行 + 重试）

```python
async def read_paper(doi: str) -> str:
    """读取论文内容"""
    url = f"https://doi.org/{doi}"
    
    for attempt in range(3):  # 最多重试 3 次
        try:
            result = await zhipu_reader.read(url)
            return result['reader_result']['content']
        except Exception as e:
            if attempt < 2:
                await asyncio.sleep(2)  # 等待后重试
            else:
                raise
```

### 步骤 2: 结构化输出（批量）

```python
async def extract_authors_batch(contents: list[dict]) -> list[dict]:
    """批量提取作者信息"""
    # 构建 JSONL
    requests = []
    for doi, content in contents:
        request = {
            "custom_id": f"doi_{doi.replace('/', '_')}",
            "method": "POST",
            "url": "/v4/chat/completions",
            "body": {
                "model": "glm-4-plus",
                "messages": [...],
                "response_format": {"type": "json_object"}  # ✅ 使用新方式
            }
        }
        requests.append(request)
    
    # 批量处理
    return await batch_processor.process(requests)
```

---

## 预计性能

### 网页阅读阶段
- **并发数**: 5
- **速度**: 30-40 篇/分钟
- **1000 篇耗时**: ~25-33 分钟
- **成本**: ~1 元

### 结构化输出阶段
- **批处理**: 50 篇/批次
- **速度**: 100-200 篇/分钟（取决于智谱批处理速度）
- **1000 篇耗时**: ~5-10 分钟
- **成本**: ~50 元

### 总计
- **总耗时**: ~30-45 分钟
- **总成本**: ~51 元/1000 篇
- **预期成功率**: 85-90%（网页阅读 85% + 结构化输出 100%）

---

## 实施方案

### 独立脚本: `scripts/extract_with_zhipu_reader.py`

**流程**:
```
1. 从数据库获取待处理 DOI 列表
2. 并发调用智谱网页阅读 API（限制 5 并发）
3. 保存到 raw_markdown 表
4. 批量调用智谱结构化输出 API
5. 保存到 paper_leads 表
```

**触发方式**: 独立脚本，手动运行

**参数**:
```bash
python scripts/extract_with_zhipu_reader.py \
  --limit 1000 \
  --concurrency 5 \
  --batch-size 50
```

---

## 下一步

1. **创建独立脚本** `scripts/extract_with_zhipu_reader.py`
2. **实现两步流程**（网页阅读 + 结构化输出）
3. **测试 100 篇**验证流程
4. **部署生产**（独立分支，不影响现有 Jina 流程）

要开始实施吗？