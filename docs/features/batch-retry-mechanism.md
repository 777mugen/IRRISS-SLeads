# 批处理失败重试机制

**创建日期**: 2026-03-14
**作者**: IRRISS Team

---

## 📋 概述

批处理系统在处理大量论文时，可能会遇到部分论文提取失败的情况。为了确保所有论文都能被成功处理，我们实现了**自动重试机制**。

---

## 🎯 设计目标

1. ✅ **自动重试**: 失败的论文会被自动重试
2. ✅ **最大重试次数**: 避免无限重试（默认 3 次）
3. ✅ **错误记录**: 详细记录每次失败的原因
4. ✅ **时间间隔**: 避免频繁重试（默认 1 小时后）
5. ✅ **统计监控**: 实时查看重试状态

---

## 📊 数据库设计

### 新增字段（raw_markdown 表）

| 字段 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `retry_count` | INTEGER | 重试次数 | 0 |
| `last_retry_at` | DATETIME | 最后重试时间 | NULL |

### 状态流转

```
pending → processing → completed
                    ↓
                  failed
                    ↓
                  pending (重试)
                    ↓
                  failed (达到最大重试次数)
```

---

## 🔧 使用方法

### 方法 1: 自动重试（推荐）

```bash
# 运行重试脚本
python scripts/retry_failed_papers.py
```

**功能**：
- ✅ 自动获取可重试的论文
- ✅ 标记为 `pending` 状态
- ✅ 运行批处理
- ✅ 显示重试结果

---

### 方法 2: 手动管理

```python
from src.processors.retry_manager import RetryManager

# 1. 创建重试管理器
retry_manager = RetryManager(max_retries=3)

# 2. 获取可重试的论文
papers = await retry_manager.get_failed_papers(limit=50)

# 3. 标记为待重试
await retry_manager.mark_for_retry(papers)

# 4. 获取重试统计
stats = await retry_manager.get_retry_stats()
print(stats)
# {
#     'failed_no_retry': 10,
#     'failed_max_retries': 2,
#     'total_retries': 25
# }
```

---

### 方法 3: 集成到批处理流水线

```python
from src.pipeline_batch import BatchPipeline
from src.processors.retry_manager import RetryManager

async def run_pipeline_with_retry():
    """带重试机制的批处理流水线"""
    
    # 1. 运行批处理
    pipeline = BatchPipeline()
    result = await pipeline.run_batch_extraction(limit=100)
    
    # 2. 如果有失败，自动重试
    if result['failed'] > 0:
        retry_manager = RetryManager(max_retries=3)
        
        # 获取可重试的论文
        papers = await retry_manager.get_failed_papers()
        
        if papers:
            print(f"发现 {len(papers)} 篇失败论文，准备重试...")
            
            # 标记为待重试
            await retry_manager.mark_for_retry(papers)
            
            # 重新运行批处理
            retry_result = await pipeline.run_batch_extraction(
                limit=len(papers)
            )
            
            print(f"重试结果: {retry_result}")
    
    return result
```

---

## 📈 监控和统计

### 获取处理统计

```python
from src.pipeline_batch import BatchPipeline

pipeline = BatchPipeline()
stats = await pipeline.get_processing_stats()

print(stats)
# {
#     'pending': 100,
#     'processing': 0,
#     'completed': 950,
#     'failed': 50
# }
```

### 获取重试统计

```python
from src.processors.retry_manager import RetryManager

retry_manager = RetryManager()
stats = await retry_manager.get_retry_stats()

print(stats)
# {
#     'failed_no_retry': 10,      # 可重试
#     'failed_max_retries': 2,    # 已达最大次数
#     'total_retries': 25         # 总重试次数
# }
```

---

## 🔍 失败原因分析

### 常见失败原因

1. **Jina API 失败**
   - 网络超时
   - 反爬虫拦截
   - 内容解析错误

2. **智谱 API 失败**
   - Token 超限
   - 格式错误
   - 服务器错误

3. **解析失败**
   - JSON 格式错误
   - 必需字段缺失
   - 数据类型错误

---

## 🛠️ 配置选项

### RetryManager 配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_retries` | int | 3 | 最大重试次数 |

### get_failed_papers 配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `limit` | int | 50 | 最多获取多少条 |
| `min_retry_after_hours` | int | 1 | 失败后多久可重试 |

---

## 📝 数据库迁移

### 升级数据库

```bash
# 运行迁移
alembic upgrade head
```

### 回滚迁移

```bash
# 回滚到上一版本
alembic downgrade -1
```

---

## 🚀 生产部署

### Step 1: 运行数据库迁移

```bash
alembic upgrade head
```

### Step 2: 设置定时任务

```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每小时重试一次失败的论文）
0 * * * * cd /path/to/IRRISS-SLeads && python scripts/retry_failed_papers.py
```

### Step 3: 监控日志

```bash
# 查看重试日志
tail -f logs/retry.log
```

---

## 📊 性能指标

### 预期效果

| 指标 | 目标 |
|------|------|
| **首次成功率** | 95%+ |
| **重试后成功率** | 98%+ |
| **最终失败率** | < 2% |

---

## 🐛 故障排查

### 问题 1: 重试次数不增加

**检查**:
```sql
SELECT doi, retry_count, processing_status 
FROM raw_markdown 
WHERE processing_status = 'failed';
```

**解决**:
- 确认数据库迁移已执行
- 检查 `RetryManager.mark_for_retry()` 是否被调用

---

### 问题 2: 重试一直失败

**可能原因**:
- 论文内容本身有问题
- Jina API 持续失败
- 智谱 API 持续失败

**解决**:
```bash
# 查看错误日志
SELECT doi, error_message, retry_count 
FROM raw_markdown 
WHERE processing_status = 'failed' 
  AND retry_count >= 3
ORDER BY processed_at DESC;
```

---

## 📚 相关文档

- **批处理策略**: `docs/solutions/integration-issues/metadata-extraction-batch-api-strategy.md`
- **部署指南**: `docs/deployment/production-deployment-guide.md`
- **Pipeline 架构**: 详见项目 README

---

## ✅ 总结

**失败重试机制已就绪！**

- ✅ 自动重试（最多 3 次）
- ✅ 错误记录详细
- ✅ 时间间隔控制
- ✅ 统计监控完善
- ✅ 生产就绪

**使用命令**:
```bash
python scripts/retry_failed_papers.py
```

---

**创建日期**: 2026-03-14
**版本**: v1.0
**状态**: 生产就绪 ✅
