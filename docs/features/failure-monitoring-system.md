# 批处理失败监控与通知系统

**创建日期**: 2026-03-15
**版本**: v1.0

---

## 📋 概述

自动监控批处理失败论文，提炼共性和特征，并通过飞书通知用户，让用户决策改进方案。

---

## 🔄 系统架构

```
批处理失败
    ↓
数据库标记
（processing_status='failed'）
（retry_count++, error_message）
    ↓
定时检查（每小时）
    ↓
FailureAnalyzer 分析
    ↓
提炼共性特征
    ↓
生成改进建议
    ↓
飞书通知用户
    ↓
用户决策
    ↓
执行改进方案
```

---

## 📊 功能特性

### 1. **自动失败标记**

每篇失败论文都会记录：
- `processing_status`: 'failed'
- `error_message`: 详细错误信息
- `retry_count`: 重试次数
- `last_retry_at`: 最后重试时间
- `processed_at`: 失败时间

---

### 2. **智能失败分析**

**FailureAnalyzer** 会自动分析：

#### 错误分类
- Jina API 失败
- 解析错误
- 内容过短
- 验证错误
- 智谱 API 错误

#### 内容特征统计
- 平均长度
- 最大/最小长度
- 包含作者信息的比例
- 包含邮箱信息的比例

#### 重试统计
- 重试分布
- 达到最大重试次数的论文
- 需要人工复核的论文

---

### 3. **改进建议生成**

自动生成针对性的改进建议：

**示例**：
```
⚠️ Jina API 失败较多（15 次）
建议：
  1. 增加 Jina API 超时时间（当前 95s → 120s）
  2. 添加重试机制（当前已实现，max_retries=3）
  3. 检查网络连接稳定性
```

---

### 4. **飞书通知**

**两种通知类型**：

#### A. 详细失败报告（立即发送）
当有论文达到最大重试次数时：
- 失败论文总数
- 失败原因分类
- 内容统计
- 改进建议
- 需要人工复核的论文列表

#### B. 每日摘要（定时发送）
每天的处理统计：
- 已完成、处理中、待处理、失败数量
- 最近失败论文（前 5 篇）
- 改进建议

---

## 🔧 配置指南

### Step 1: 数据库迁移

```bash
# 升级数据库（添加重试字段）
alembic upgrade head
```

---

### Step 2: 配置飞书 Webhook

#### 创建飞书机器人

1. 打开飞书群聊
2. 点击右上角 `...` → `群机器人` → `添加机器人`
3. 选择 `自定义机器人`
4. 复制 Webhook URL

#### 配置环境变量

```bash
# 编辑 .env 文件
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
```

---

### Step 3: 测试飞书通知

```bash
# 发送测试通知
python scripts/feishu_notifier.py
```

**预期结果**：
- 飞书收到测试消息
- 内容包含测试项目列表

---

### Step 4: 设置定时任务

#### 方案 A: 使用 Cron（推荐）

```bash
# 编辑 crontab
crontab -e

# 添加以下任务（每小时检查一次）
0 * * * * cd /path/to/IRRISS-SLeads && /path/to/.venv/bin/python scripts/scheduled_failure_check.py >> logs/failure_check.log 2>&1

# 每日摘要（每天 09:00）
0 9 * * * cd /path/to/IRRISS-SLeads && /path/to/.venv/bin/python scripts/feishu_notifier.py --daily >> logs/daily_summary.log 2>&1
```

---

#### 方案 B: 使用 Python 定时任务

```python
# main.py
import asyncio
import schedule
from src.processors.failure_analyzer import FailureAnalyzer
from scripts.feishu_notifier import FeishuNotifier


async def scheduled_check():
    """定时检查"""
    analyzer = FailureAnalyzer()
    retry_stats = await analyzer.check_retry_attempts()
    
    notifier = FeishuNotifier()
    
    if retry_stats['needs_manual_review']:
        await notifier.notify_batch_failures()
    elif retry_stats['max_retry_count'] > 0:
        await notifier.send_daily_summary()


# 每小时检查一次
schedule.every().hour.do(scheduled_check)

# 每天 09:00 发送摘要
schedule.every().day.at("09:00").do(scheduled_check)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## 📊 通知示例

### 示例 1: 详细失败报告

```markdown
# 批处理失败分析报告

**生成时间**: 2026-03-15 00:00:00

## 📊 总体统计

- **失败论文总数**: 15 篇
- **已达最大重试次数**: 3 篇

## 📈 失败原因分类

- **jina_api**: 8 篇 (53.3%)
- **parse_error**: 4 篇 (26.7%)
- **content_short**: 3 篇 (20.0%)

## 📏 内容统计

- **平均长度**: 45,000 字符
- **最大长度**: 120,000 字符
- **最小长度**: 500 字符
- **包含作者信息**: 12/15 篇
- **包含邮箱信息**: 10/15 篇

## 🔧 改进建议

1. ⚠️ Jina API 失败较多（8 次）
   建议：
     1. 增加 Jina API 超时时间（当前 95s → 120s）
     2. 添加重试机制（当前已实现，max_retries=3）
     3. 检查网络连接稳定性

2. ⚠️ 内容过短较多（3 次）
   可能原因：
     1. 付费墙拦截
     2. 反爬虫机制
     3. DOI 不存在
   建议：标记为人工复核

## ⚠️ 需要人工复核

有 **3** 篇论文已达到最大重试次数（3次），建议人工复核。

1. **10.1136/jitc-2025-014040**
   - 失败次数: 3
   - 错误: Jina API timeout

2. **10.21037/tcr-2025-aw-2287**
   - 失败次数: 3
   - 错误: Content too short

3. **10.1097/CM9.0000000000004035**
   - 失败次数: 3
   - 错误: Parse error
```

---

### 示例 2: 每日摘要

```markdown
# 📊 每日批处理摘要

**时间**: 2026-03-15 09:00

## 处理统计

- ✅ **已完成**: 950 篇
- ⏳ **处理中**: 0 篇
- 📋 **待处理**: 50 篇
- ❌ **失败**: 15 篇

## ⚠️ 最近失败论文

1. **10.1136/jitc-2025-014040**
   - 错误: Jina API timeout
   - 重试: 3 次

2. **10.21037/tcr-2025-aw-2287**
   - 错误: Content too short
   - 重试: 2 次

## 🔧 改进建议

- ⚠️ Jina API 失败较多（8 次）
  建议：增加超时时间、检查网络

- ⚠️ 内容过短较多（3 次）
  可能原因：付费墙、反爬虫、DOI 不存在
```

---

## 🎯 用户决策流程

### 收到通知后的决策

#### 1. **检查失败论文**
```bash
# 查看失败详情
python scripts/retry_failed_papers.py
```

#### 2. **浏览器验证**
```bash
# 手动打开论文
open "https://doi.org/10.1136/jitc-2025-014040"
```

#### 3. **决策改进方案**

根据失败原因选择：

**Jina API 失败**：
- 增加超时时间
- 检查网络连接
- 使用代理

**内容过短**：
- 检查是否付费墙
- 标记为人工处理
- 更换数据源

**解析错误**：
- 优化 Prompt
- 增加容错处理
- 调整提取规则

---

## 🔍 手动操作

### 查看失败论文

```bash
# 查看所有失败论文
python scripts/retry_failed_papers.py

# 查看失败统计
python -c "
from src.processors.failure_analyzer import FailureAnalyzer
import asyncio

async def check():
    analyzer = FailureAnalyzer()
    stats = await analyzer.get_processing_stats()
    print(stats)

asyncio.run(check())
"
```

---

### 手动发送通知

```bash
# 发送失败报告
python scripts/scheduled_failure_check.py

# 发送每日摘要
python scripts/feishu_notifier.py --daily
```

---

### 手动重试

```bash
# 重试失败的论文
python scripts/retry_failed_papers.py
```

---

## 📚 相关文档

- **重试机制**: `docs/features/batch-retry-mechanism.md`
- **批处理策略**: `docs/solutions/integration-issues/metadata-extraction-batch-api-strategy.md`
- **部署指南**: `docs/deployment/production-deployment-guide.md`

---

## ✅ 总结

**失败监控系统已完善！**

### 核心功能

1. ✅ **自动失败标记**: 详细记录失败信息
2. ✅ **智能分析**: 提炼共性和特征
3. ✅ **改进建议**: 自动生成解决方案
4. ✅ **飞书通知**: 实时通知用户
5. ✅ **用户决策**: 让用户决定改进方案

### 使用命令

```bash
# 测试飞书通知
python scripts/feishu_notifier.py

# 手动检查失败
python scripts/scheduled_failure_check.py

# 重试失败论文
python scripts/retry_failed_papers.py
```

---

**创建日期**: 2026-03-15
**版本**: v1.0
**状态**: 生产就绪 ✅
