---
title: feat: Add Web Dashboard for IRRISS-SLeads
type: feat
status: active
date: 2026-03-15
origin: docs/brainstorms/2026-03-15-web-dashboard-brainstorm.md
---

# feat: Add Web Dashboard for IRRISS-SLeads

## Overview

为 IRRISS-SLeads 系统开发一个综合型 Web Dashboard，集成批处理监控、DOI 查询、数据分析、配置管理、CSV 导入导出等功能。采用 FastAPI + Jinja2 + HTMX + Tailwind CSS 技术栈，实现快速开发和流畅的用户体验。

Dashboard 主要服务于内部用户（开发人员和销售团队），提供实时的批处理状态监控、线索查询、数据分析和销售反馈收集功能。

## Problem Statement / Motivation

### 当前问题

1. **缺乏可视化界面**: 所有操作需要通过命令行或直接查询数据库
2. **监控困难**: 无法实时查看批处理任务状态和失败原因
3. **查询不便**: 检查论文提取结果需要手动执行 SQL 查询
4. **反馈收集低效**: 销售反馈需要通过邮件或 Excel 表格传递
5. **数据分析缺失**: 无法直观看到机构分布、提取质量等统计信息

### 目标

提供一个**单页多标签的 Web Dashboard**，让开发和销售团队能够：
- 实时监控批处理任务状态
- 快速查询论文提取结果
- 可视化数据分析（机构分布、统计图表）
- 方便地导入导出 CSV 文件
- 管理关键词和评分规则配置

## Proposed Solution

### 技术架构

```
浏览器
  ↓
FastAPI (Web Framework)
  ↓
HTMX (局部刷新，无页面跳转)
  ↓
Jinja2 Templates (服务器端渲染)
  ↓
Tailwind CSS (样式)
  ↓
ECharts (图表和中国地图)
  ↓
SQLAlchemy Async (数据库访问)
  ↓
PostgreSQL (数据存储)
```

### 页面结构

**单页多标签设计**（7 个标签）:

1. **📊 监控标签** - 批处理任务状态 + 失败列表
2. **🔍 查询标签** - DOI 查询 + 结果展示
3. **📈 分析标签** - 数据总览 + 机构分布地图
4. **⚙️ 配置标签** - 关键词管理 + 评分规则
5. **📤 导入导出标签** - CSV 下载 + 上传
6. **📝 日志标签** - 系统日志（可选）
7. **ℹ️ 帮助标签** - 使用说明（可选）

### 文件结构

```
src/web/
├── __init__.py
├── main.py                  # FastAPI 应用入口
├── routes/                  # 路由层
│   ├── __init__.py
│   ├── dashboard.py         # Dashboard 首页
│   ├── batch.py             # 批处理监控
│   ├── query.py             # DOI 查询
│   ├── analysis.py          # 数据分析
│   ├── config.py            # 配置管理
│   └── export.py            # CSV 导入导出
├── api/                     # REST API 层
│   ├── __init__.py
│   ├── batch.py             # 批处理 API
│   ├── query.py             # 查询 API
│   ├── config.py            # 配置 API
│   └── export.py            # 导出 API
├── services/                # 业务逻辑层
│   ├── __init__.py
│   ├── batch_service.py     # 批处理业务逻辑
│   ├── query_service.py     # 查询业务逻辑
│   ├── analysis_service.py  # 分析业务逻辑
│   └── export_service.py    # 导出业务逻辑
├── templates/               # Jinja2 模板
│   ├── base.html            # 基础模板（含 Tailwind + HTMX）
│   ├── dashboard/
│   │   └── index.html       # Dashboard 首页
│   ├── batch/
│   │   ├── monitor.html     # 批处理监控
│   │   └── failed.html      # 失败列表
│   ├── query/
│   │   ├── search.html      # DOI 查询表单
│   │   └── result.html      # 查询结果
│   ├── analysis/
│   │   ├── stats.html       # 统计图表
│   │   └── map.html         # 机构分布地图
│   ├── config/
│   │   ├── keywords.html    # 关键词管理
│   │   └── scoring.html     # 评分规则
│   └── export/
│       └── index.html       # 导入导出界面
└── static/                  # 静态文件
    ├── css/
    │   └── dashboard.css    # 自定义样式
    └── js/
        ├── htmx-config.js   # HTMX 配置
        ├── charts.js        # ECharts 图表
        └── map.js           # 地图相关
```

## Technical Considerations

### 1. 依赖管理

**需要添加到 requirements.txt**:
```txt
fastapi>=0.109.0
jinja2>=3.1.0
uvicorn[standard]>=0.27.0
python-multipart>=0.0.6  # 文件上传
aiofiles>=23.0.0         # 异步文件操作
```

**已存在的依赖（可复用）**:
```txt
sqlalchemy>=2.0.0
asyncpg>=0.29.0
pandas>=2.2.0
pyyaml>=6.0
structlog>=24.1.0
```

### 2. 数据库集成

**复用现有模型**（无需迁移）:
- ✅ `PaperLead` - 论文线索
- ✅ `RawMarkdown` - 原始 Markdown + 批处理状态
- ✅ `Feedback` - 销售反馈
- ✅ `TenderLead` - 招标线索

**关键查询**:
```python
# DOI 查询
async def query_doi(doi: str):
    raw = await session.execute(
        select(RawMarkdown).where(RawMarkdown.doi == doi)
    )
    paper = await session.execute(
        select(PaperLead).where(PaperLead.doi == doi)
    )
    return raw.scalar(), paper.scalar()

# 批处理监控
async def get_batch_stats():
    stats = await session.execute(
        select(
            RawMarkdown.processing_status,
            func.count(RawMarkdown.id)
        ).group_by(RawMarkdown.processing_status)
    )
    return dict(stats.all())
```

### 3. 配置管理

**复用现有配置文件**:
- `config/keywords.yaml` - 搜索关键词
- `config/scoring_paper.yaml` - 评分规则

**配置加载**:
```python
from src.config.loader import load_config

config = load_config()
keywords = config.keywords
scoring = config.scoring_paper
```

### 4. 实时刷新策略

**批处理状态刷新**:
- ✅ 每 1 分钟自动刷新（HTMX `hx-trigger="every 60s"`）
- ✅ 手动刷新按钮

**示例**:
```html
<div hx-get="/api/batch/stats"
     hx-trigger="every 60s, click from:#refresh-btn"
     hx-swap="innerHTML">
    <!-- 批处理统计卡片 -->
</div>
```

### 5. CSV 导入导出

**复用现有 CSVExporter**:
```python
from src.exporters.csv_exporter import CSVExporter

exporter = CSVExporter()
await exporter.export_paper_leads(
    output_path="output/paper_leads/full_export.csv",
    filters={"date": "today"}
)
```

**CSV 导入流程**:
1. 用户上传 CSV → 临时保存
2. 预览解析结果 → 显示匹配到的 DOI
3. 用户确认 → 更新 Feedback 表
4. 返回成功/失败统计

### 6. 机构分布地图

**数据来源**: `PaperLead.address_cn` 字段

**城市提取逻辑**:
```python
import re

CITIES = ["北京", "上海", "广州", "深圳", "杭州", ...]

def extract_city(address_cn: str) -> str:
    for city in CITIES:
        if city in address_cn:
            return city
    return "未知"
```

**ECharts 中国地图**:
```javascript
// 统计每个城市的论文数量
const cityData = [
    {name: '北京', value: 150},
    {name: '上海', value: 120},
    ...
];

// 渲染地图
echarts.init(document.getElementById('map')).setOption({
    series: [{
        type: 'map',
        map: 'china',
        data: cityData
    }]
});
```

### 7. 安全考虑

- ✅ **无需认证**（内网访问）
- ✅ **SQL 注入防护**（SQLAlchemy 参数化查询）
- ✅ **XSS 防护**（Jinja2 自动转义）
- ⚠️ **未来扩展**：可添加 Basic Auth

## System-Wide Impact

### Interaction Graph

**批处理监控触发链**:
```
用户访问 /dashboard
  → FastAPI route (dashboard.py)
  → BatchService.get_batch_stats()
  → BatchMonitor.check_stale_tasks()
  → Database query (RawMarkdown)
  → Return statistics
  → Jinja2 render (dashboard/index.html)
  → HTMX auto-refresh (every 60s)
```

**CSV 上传触发链**:
```
用户上传 CSV
  → FastAPI route (export.py)
  → ExportService.upload_feedback_csv()
  → Pandas read CSV
  → Validate DOI exists in PaperLead
  → Preview results
  → User confirms
  → Update Feedback table
  → Return success stats
```

### Error Propagation

**错误处理层级**:
1. **网络层**: HTTP 连接错误 → 返回 503
2. **应用层**: 业务逻辑错误 → 返回 400 + 错误消息
3. **数据库层**: SQL 错误 → 返回 500 + 日志记录
4. **文件层**: CSV 解析错误 → 返回 400 + 详细错误行号

**错误追踪**:
```python
import structlog

logger = structlog.get_logger()

try:
    await service.process_csv(file)
except Exception as e:
    logger.error("csv_upload_failed", error=str(e), file=file.filename)
    raise HTTPException(status_code=400, detail=str(e))
```

### State Lifecycle Risks

**CSV 上传状态风险**:
- ⚠️ **部分成功风险**: 10 条数据，8 条成功，2 条失败 → 数据库处于不一致状态
- ✅ **解决方案**: 使用数据库事务，失败时回滚

```python
async with session.begin():
    for row in csv_data:
        feedback = Feedback(**row)
        session.add(feedback)
    # 提交事务，失败时自动回滚
```

**批处理状态风险**:
- ⚠️ **僵尸任务**: processing_status = "processing" 但任务已死
- ✅ **解决方案**: 复用现有 BatchMonitor 的 `check_stale_tasks()`

### API Surface Parity

**现有接口**:
- ❌ 无 Web API（需要全部新建）

**新接口**:
- ✅ `/api/batch/stats` - 批处理统计
- ✅ `/api/query/doi` - DOI 查询
- ✅ `/api/config/keywords` - 关键词配置
- ✅ `/api/export/csv` - CSV 导出
- ✅ `/api/import/csv` - CSV 导入

### Integration Test Scenarios

**场景 1: 批处理监控实时性**
```python
# 测试目标: 验证批处理状态每 1 分钟自动刷新
async def test_batch_refresh():
    # 1. 创建一个批处理任务
    batch_id = await create_batch()
    
    # 2. 访问 Dashboard
    response = await client.get("/dashboard")
    assert batch_id in response.text
    
    # 3. 更新批处理状态
    await update_batch_status(batch_id, "completed")
    
    # 4. 等待 60 秒后检查（或手动触发刷新）
    response = await client.get("/api/batch/stats")
    assert "completed" in response.json()["status"]
```

**场景 2: CSV 上传和预览**
```python
# 测试目标: 验证 CSV 上传 → 预览 → 确认流程
async def test_csv_upload():
    # 1. 上传 CSV
    csv_content = "DOI,线索准确性\n10.xxx,好"
    response = await client.post(
        "/api/import/csv",
        files={"file": ("feedback.csv", csv_content)}
    )
    
    # 2. 检查预览结果
    assert response.json()["preview"]["matched_dois"] == 1
    
    # 3. 确认上传
    response = await client.post(
        "/api/import/csv/confirm",
        json={"upload_id": response.json()["upload_id"]}
    )
    
    # 4. 验证数据库更新
    feedback = await session.execute(
        select(Feedback).where(Feedback.paper_lead_id == paper_id)
    )
    assert feedback.scalar().accuracy == "好"
```

**场景 3: 机构分布地图数据**
```python
# 测试目标: 验证城市提取和地图数据生成
async def test_institution_map():
    # 1. 创建测试数据
    await create_paper_lead(
        address_cn="上海市浦东新区张江高科技园区"
    )
    
    # 2. 获取地图数据
    response = await client.get("/api/analysis/map")
    city_data = response.json()["cities"]
    
    # 3. 验证上海计数
    shanghai = next(c for c in city_data if c["name"] == "上海")
    assert shanghai["value"] >= 1
```

## Acceptance Criteria

### 功能需求

- [ ] **监控标签**: 显示批处理任务状态（pending/processing/completed/failed）
- [ ] **监控标签**: 显示失败论文列表（DOI、错误信息、重试按钮）
- [ ] **监控标签**: 每 1 分钟自动刷新状态
- [ ] **查询标签**: 输入 DOI 查询 raw_markdown 表是否存在
- [ ] **查询标签**: 输入 DOI 查询 paper_leads 表是否存在
- [ ] **查询标签**: 展示已提取论文的所有字段（作者、邮箱、地址等）
- [ ] **分析标签**: 数据总览卡片（总论文数、作者数、机构数）
- [ ] **分析标签**: 机构分布地图（中国热力图，基于 address_cn）
- [ ] **分析标签**: 提取质量统计（字段完整度、评分分布）
- [ ] **配置标签**: 展示关键词配置（config/keywords.yaml）
- [ ] **配置标签**: 展示评分规则（config/scoring_paper.yaml）
- [ ] **配置标签**: 支持编辑关键词（保存到 YAML 文件）
- [ ] **导入导出标签**: 下载全量 CSV
- [ ] **导入导出标签**: 下载当日新增 CSV
- [ ] **导入导出标签**: 上传销售反馈 CSV
- [ ] **导入导出标签**: 预览解析结果（显示匹配到的 DOI）
- [ ] **导入导出标签**: 确认后更新到 Feedback 表

### 非功能需求

- [ ] **性能**: 页面加载时间 < 2 秒
- [ ] **响应式**: 支持桌面和移动设备
- [ ] **可访问性**: 支持键盘导航
- [ ] **错误处理**: 友好的错误提示
- [ ] **日志**: 记录关键操作（上传、查询、重试）

### 质量门禁

- [ ] **测试覆盖**: 核心业务逻辑测试覆盖率 > 80%
- [ ] **文档**: 更新 README.md，添加 Dashboard 使用说明
- [ ] **代码审查**: 通过 DHH Rails Reviewer 和 Code Simplicity Reviewer
- [ ] **部署**: 更新部署文档（docs/deployment/）

## Success Metrics

### 量化指标

1. **使用率**: 每周访问次数 > 50 次
2. **效率提升**: 查询时间从 5 分钟降至 < 10 秒
3. **错误率**: 页面错误率 < 1%
4. **反馈收集**: 销售反馈收集率从 20% 提升至 > 80%

### 定性指标

1. **用户满意度**: 开发和销售团队反馈积极
2. **易用性**: 无需培训即可使用
3. **可维护性**: 代码结构清晰，易于扩展

## Dependencies & Prerequisites

### 技术依赖

**必需依赖**（需添加到 requirements.txt）:
- ✅ FastAPI >= 0.109.0
- ✅ Jinja2 >= 3.1.0
- ✅ Uvicorn[standard] >= 0.27.0
- ✅ python-multipart >= 0.0.6
- ✅ aiofiles >= 23.0.0

**已存在依赖**:
- ✅ SQLAlchemy >= 2.0.0
- ✅ asyncpg >= 0.29.0
- ✅ Pandas >= 2.2.0
- ✅ PyYAML >= 6.0
- ✅ structlog >= 24.1.0

### 前置条件

- ✅ PostgreSQL 数据库已部署
- ✅ 现有批处理系统正常运行
- ✅ 配置文件（keywords.yaml, scoring_paper.yaml）已存在
- ✅ 销售反馈表（Feedback）已创建

### 外部服务

- ✅ **CDN**: Tailwind CSS、ECharts（通过 CDN 引入）
- ✅ **无其他外部服务依赖**

## Risk Analysis & Mitigation

### 高风险

**风险 1: 批处理监控性能瓶颈**
- **描述**: 大量批处理任务时，查询可能变慢
- **缓解**: 
  - 添加数据库索引（processing_status, batch_id）
  - 使用分页查询
  - 缓存统计数据（Redis）
- **应急计划**: 限制显示最近 7 天的任务

**风险 2: CSV 上传文件过大**
- **描述**: 用户上传 100MB+ 的 CSV 文件
- **缓解**:
  - 限制文件大小（10MB）
  - 流式处理（Pandas chunksize）
  - 后台异步处理
- **应急计划**: 拒绝大文件，提示用户分割

### 中风险

**风险 3: 关键词配置编辑冲突**
- **描述**: 多人同时编辑 keywords.yaml
- **缓解**:
  - 添加文件锁
  - 记录编辑时间戳
  - 冲突提示
- **应急计划**: 保留编辑历史，可回滚

**风险 4: 机构分布地图数据不准确**
- **描述**: address_cn 字段无法提取城市
- **缓解**:
  - 扩充城市列表
  - 支持手动标记
  - 显示"未知"类别
- **应急计划**: 跳过无法识别的地址

### 低风险

**风险 5: 浏览器兼容性**
- **描述**: HTMX 在旧浏览器不支持
- **缓解**: 使用现代浏览器（Chrome, Firefox, Safari 最新版）
- **应急计划**: 提供降级版本（纯 HTML 表单）

## Resource Requirements

### 人力资源

- **开发**: 1 人 × 5-7 天
- **测试**: 0.5 人 × 2 天
- **文档**: 0.5 人 × 1 天

### 基础设施

- **服务器**: 复用现有服务器（无需额外资源）
- **数据库**: 复用现有 PostgreSQL
- **存储**: 临时 CSV 存储 < 1GB

### 时间表

**Phase 1: MVP（2 天）**
- Day 1: 搭建 FastAPI 框架 + 监控标签
- Day 2: DOI 查询标签 + 基础样式

**Phase 2: 核心功能（2 天）**
- Day 3: 导入导出标签 + 分析标签
- Day 4: 配置标签 + 日志标签

**Phase 3: 优化（1-2 天）**
- Day 5: 性能优化 + 响应式设计
- Day 6-7: 测试 + 文档

## Future Considerations

### 可扩展性

**短期扩展（3 个月内）**:
- 添加 WebSocket 实时推送（替代轮询）
- 添加用户认证（Basic Auth）
- 支持更多图表类型（趋势图、对比图）

**长期扩展（6 个月以上）**:
- 移动端 App
- API 开放给外部系统
- 机器学习模型集成（预测线索质量）

### 技术债务

**潜在债务**:
- ⚠️ CDN 依赖（Tailwind、ECharts）→ 考虑本地化
- ⚠️ 无缓存层 → 添加 Redis
- ⚠️ 无监控 → 添加 Prometheus + Grafana

## Documentation Plan

### 需要更新的文档

- [ ] **README.md**: 添加 Dashboard 使用说明
- [ ] **docs/deployment/**: 更新部署指南（FastAPI 启动命令）
- [ ] **docs/architecture/**: 添加 Web 层架构说明
- [ ] **docs/api/**: 添加 REST API 文档

### 新建文档

- [ ] **docs/dashboard/user-guide.md**: Dashboard 用户手册
- [ ] **docs/dashboard/api-reference.md**: API 参考文档
- [ ] **docs/dashboard/troubleshooting.md**: 故障排查指南

## Sources & References

### Origin

- **Brainstorm document**: [docs/brainstorms/2026-03-15-web-dashboard-brainstorm.md](../brainstorms/2026-03-15-web-dashboard-brainstorm.md)
  - **Key decisions carried forward**:
    1. 技术栈：FastAPI + Jinja2 + HTMX + Tailwind CSS
    2. 页面结构：单页多标签（7 个标签）
    3. 数据模型：复用现有 Feedback 表
    4. 配置管理：YAML 文件（keywords.yaml, scoring_paper.yaml）
    5. CSV 处理：Pandas（预览 → 确认 → 更新）

### Internal References

**Database Models**:
- `src/db/models.py:42` - PaperLead model
- `src/db/models.py:108` - RawMarkdown model (with processing_status)
- `src/db/models.py:145` - Feedback model (5 dimensions)

**Batch Processing**:
- `src/monitoring/batch_monitor.py` - BatchMonitor class
- `src/processors/batch_processor.py` - BatchProcessor class
- `src/pipeline_batch.py` - BatchPipeline class

**Configuration**:
- `config/keywords.yaml` - Search keywords
- `config/scoring_paper.yaml` - Paper scoring rules
- `src/config/loader.py` - YAML config loader

**Export**:
- `src/exporters/csv_exporter.py` - CSVExporter class

### External References

**FastAPI**:
- Documentation: https://fastapi.tiangolo.com/
- Tutorial: https://fastapi.tiangolo.com/tutorial/

**Jinja2**:
- Documentation: https://jinja.palletsprojects.com/
- Template designer: https://jinja.palletsprojects.com/en/3.1.x/templates/

**HTMX**:
- Documentation: https://htmx.org/
- Examples: https://htmx.org/examples/

**ECharts**:
- Documentation: https://echarts.apache.org/
- China map: https://echarts.apache.org/examples/zh/editor.html?c=map-polygon

**Tailwind CSS**:
- Documentation: https://tailwindcss.com/
- CDN: https://cdn.tailwindcss.com

### Best Practices

**From docs/solutions/**:
- `zhipu-batch-api-integration.md`: State machine for batch processing
- `metadata-extraction-batch-api-strategy.md`: Never truncate content
- `v1-batch-strategy-decision.md`: Accuracy > Token consumption
- `2026-03-13-jina-api-optimization.md`: API parameter tuning

### Related Work

- **PR #3**: https://github.com/777mugen/IRRISS-SLeads/pull/3 (Batch processing integration)
- **Commit da79e8a**: feat: adopt V1 strategy
- **Commit e91176b**: feat: add batch retry mechanism

---

## Implementation Checklist

### Phase 1: Foundation (Day 1-2)

- [ ] 添加依赖到 requirements.txt
- [ ] 创建 `src/web/` 目录结构
- [ ] 实现 FastAPI 应用入口（main.py）
- [ ] 创建 base.html 模板（Tailwind + HTMX）
- [ ] 实现监控标签（批处理状态 + 失败列表）
- [ ] 实现 DOI 查询标签（查询 + 结果展示）
- [ ] 添加基础样式（Tailwind）

### Phase 2: Features (Day 3-4)

- [ ] 实现导入导出标签（CSV 下载 + 上传）
- [ ] 实现分析标签（统计图表 + 机构分布地图）
- [ ] 实现配置标签（关键词 + 评分规则展示）
- [ ] 实现日志标签（系统日志查看）
- [ ] 添加 ECharts 中国地图

### Phase 3: Optimization (Day 5-7)

- [ ] 性能优化（数据库查询、缓存）
- [ ] 响应式设计（移动端适配）
- [ ] 错误处理和用户提示
- [ ] 单元测试和集成测试
- [ ] 文档更新（README, API 文档）
- [ ] 代码审查和优化

---

**Plan Status**: ✅ Ready for implementation (Deepened)
**Estimated Effort**: 5-7 days
**Priority**: High
**Assignee**: TBD

---

## Enhancement Summary

**Deepened on:** 2026-03-15
**Sections enhanced:** 8 major sections
**Research agents used:** 4 parallel agents (Performance, Frontend Design, Security, Best Practices)

### Key Improvements

1. **性能优化策略**
   - ✅ Redis 缓存策略：批处理统计 60s TTL、DOI 查询 5min TTL、地图数据 1h TTL
   - ✅ 数据库索引优化：processing_status, batch_id, created_at 复合索引
   - ✅ 异步并发查询：`asyncio.gather()` 同时查询多个表
   - ✅ 连接池配置：pool_size=20, max_overflow=10

2. **前端设计模式**
   - ✅ 侧边栏布局：固定宽度 240-280px，移动端可折叠
   - ✅ 卡片式统计：CSS Grid 响应式布局（1/2/4 列）
   - ✅ ECharts 配置：中国地图散点图、环形状态图、趋势折线图
   - ✅ 响应式策略：移动优先，`sm:`, `md:`, `lg:` 断点

3. **安全增强措施**
   - ✅ 文件上传安全：10MB 限制、类型验证、事务保护
   - ✅ 输入验证：DOI 正则、CSV 列验证、YAML schema
   - ✅ 审计日志：记录 CSV_UPLOAD, DOI_QUERY, CONFIG_EDIT 事件
   - ✅ 未来认证：Basic Auth 环境变量配置

4. **最佳实践集成**
   - ✅ FastAPI 架构：路由层 + API 层 + 服务层分离
   - ✅ Jinja2 模板：base.html → 页面模板 → 组件宏
   - ✅ CSV 处理：流式上传（aiofiles）+ 预览 + 确认流程
   - ✅ 测试策略：单元测试（Mock DB）+ 集成测试（测试 DB）

### New Considerations Discovered

#### 实时更新策略
- **MVP 阶段**: HTMX 轮询（每 60 秒）- `hx-trigger="every 60s"`
- **生产环境**: 迁移到 WebSocket 或 Server-Sent Events (SSE)
- **迁移路径**: Phase 1 (HTMX polling) → Phase 2 (WebSocket) → Phase 3 (SSE)

#### 文件上传流程
```
用户上传 CSV
  → 临时保存（aiofiles）
  → Pandas 解析（chunksize=1000）
  → 预览解析结果（显示匹配 DOI）
  → 用户确认
  → 事务更新（Feedback 表）
  → 返回成功/失败统计
```

#### 中国地图数据
- **数据来源**: `paper_leads.address_cn` 字段
- **城市提取**: 预定义城市列表（北京、上海、广州等）
- **缓存策略**: 预聚合城市统计，Redis 缓存 1h TTL
- **地图配置**: ECharts 散点图，根据论文数量调整点大小

#### 性能监控指标
- **页面加载时间**: < 2 秒（Prometheus histogram）
- **API 响应时间**: < 500ms p95（FastAPI middleware）
- **数据库查询延迟**: < 100ms p95（SQLAlchemy events）
- **并发用户容量**: 10 用户（Stage 1）→ 500+ 用户（Stage 4）

### Research Sources

1. **Performance Research** (2m 21s)
   - Database optimization patterns
   - Caching strategies (Redis)
   - Async file operations
   - Real-time update strategies

2. **Frontend Design Research** (2m 30s)
   - Dashboard layout patterns
   - Component design best practices
   - Responsive strategies
   - ECharts configuration

3. **Security Research** (3m 15s)
   - Input validation patterns
   - File upload security
   - Secrets management
   - Audit logging

4. **Best Practices Research** (6m 6s)
   - FastAPI architecture patterns
   - Jinja2 template organization
   - CSV upload/download flows
   - Database query optimization

---

**Deepening complete. Plan ready for implementation with enhanced depth and grounding.**
