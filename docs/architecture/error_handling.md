# 异常处理与日志规范

## 异常处理

### 网络请求
- **网站不可用 / 超时**: 重试 1 次
- **验证码**: 立即通知 shane，不自动处理
- **失败数据**: 当日不入库，次日重试（status=pending_retry）

### API 调用
- **PubMed Entrez API**: 
  - 速率限制 3 requests/second
  - 超时重试（最多3次）
- **NCBI ID Converter API**:
  - 转换失败 → 记录日志，跳过该 PMID
- **Jina Reader API**（优化版）:
  - **付费用户**: 15 个优化参数，反爬虫拦截 <10%
  - 失败 → 切换 Playwright（兜底方案）
  - 超时: 60 秒
  - 缓存: 1 小时
- **智谱批量 API**:
  - 提交失败 → 重试（最多 3 次）
  - 任务超时 → 查询任务状态，等待完成
  - 部分失败 → 解析成功的条目，记录失败的 DOI
  - JSON 解析失败 → 记录原始响应，标记为"提取失败"

### 数据处理
- **DOI 缺失**: 允许 NULL，但有值时必须唯一
- **字段缺失**: 触发重新爬取逻辑
- **单条数据失败**: 不中断整体任务
- **外部 API 失败**: try/except 记录日志后继续

---

## 增量爬取异常处理

### 字段完整性检查
```python
required_fields = [
    'title', 'published_at', 'article_url', 'source',
    'name', 'address', 'phone', 'email'
]

if DOI 不存在:
    # 新线索，正常处理
    处理并入库
elif DOI 存在:
    检查所有 required_fields
    if 所有字段存在:
        跳过
    else:
        # 字段缺失，重新提取
        从 raw_markdown 重新提取
        更新数据库
        发送飞书通知
```

### 重新提取失败
- 记录到日志
- 标记 status='extract_failed'
- 不影响其他数据处理

---

## 日志

### 日志配置
- **使用**: Python logging
- **目录**: logs/
- **级别**: DEBUG / INFO / WARNING / ERROR
- **保留**: 30 天

### 日志文件
```
logs/
├── sleads_2026-03-12.log    # 主日志
├── api_2026-03-12.log        # API 调用日志
└── error_2026-03-12.log      # 错误日志
```

### 日志格式
```
[时间戳] [级别] [模块] 消息
[2026-03-12 08:00:00] [INFO] [pipeline] 处理论文: DOI=10.xxxx/xxxxx
[2026-03-12 08:00:05] [WARNING] [llm.extractor] JSON 解析失败: DOI=10.xxxx/xxxxx
```

---

## 批处理错误处理最佳实践

### 批量提交失败
```python
async def submit_batch_with_retry(jsonl_file: Path, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            batch_id = await batch_client.submit_batch(jsonl_file)
            return batch_id
        except Exception as e:
            logger.warning(f"批处理提交失败（尝试 {attempt+1}/{max_retries}）: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(10 * (attempt + 1))  # 指数退避
    
    raise Exception(f"批处理提交失败，已重试 {max_retries} 次")
```

### 批量结果解析
```python
def parse_batch_results(output_file: Path) -> dict:
    """解析批量结果，容忍部分失败"""
    success_count = 0
    failed_dois = []
    
    with open(output_file, 'r') as f:
        for line in f:
            try:
                result = json.loads(line)
                if result.get('status_code') == 200:
                    # 解析成功
                    success_count += 1
                else:
                    # 单条失败
                    doi = result.get('custom_id', '').replace('doi_', '')
                    failed_dois.append(doi)
            except json.JSONDecodeError as e:
                logger.error(f"JSON 解析失败: {e}")
    
    return {
        'success_count': success_count,
        'failed_dois': failed_dois,
        'success_rate': success_count / (success_count + len(failed_dois))
    }
```

### 字段验证
```python
def validate_extraction(data: dict) -> bool:
    """验证提取结果的完整性"""
    required_fields = ['title', 'published_at', 'corresponding_author']
    
    for field in required_fields:
        if field not in data or data[field] is None:
            logger.warning(f"字段缺失: {field}")
            return False
    
    # 验证通讯作者字段
    author = data.get('corresponding_author', {})
    if not author.get('name') or not author.get('email'):
        logger.warning("通讯作者信息不完整")
        return False
    
    return True
```

---

## 通知

### 飞书通知场景
1. **每日任务完成**: 发送摘要
   - 论文：X 篇
   - 处理：X 篇
   - 导出：X 条
   - 耗时：X 分钟

2. **异常告警**: 
   - 验证码出现
   - API 连续失败（>3次）
   - 数据库连接失败

3. **字段更新确认**:
   - DOI 已存在但字段缺失
   - 重新提取后发送 diff 报告
   - 等待人工确认后更新

### MVP 阶段
- ✅ 仅日志记录
- ✅ 飞书通知已实现
