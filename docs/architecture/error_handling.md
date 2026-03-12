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
- **Jina Reader API**:
  - 失败 → 切换 Playwright
- **GLM-5 API**:
  - **429 错误**: 从响应头读取 Retry-After，等待后重试
  - **速率控制**: 高峰期30秒/请求，非高峰20秒/请求
  - **JSON 解析失败**: 记录原始响应，标记为"提取失败"

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
