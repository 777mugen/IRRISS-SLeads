# 架构文档索引

本目录包含 IRRISS-SLeads 系统的架构设计文档。

---

## 📚 核心文档

### 系统概览
- **[architecture_overview.md](architecture_overview.md)** - 系统架构总览
  - 数据流向
  - 7 层架构设计
  - 批处理模式
  - 关键设计原则

### 数据层
- **[data_sources.md](data_sources.md)** - 数据源集成
  - PubMed Entrez API
  - NCBI ID Converter API
  - Jina Reader API（优化版）⭐
  - 招标数据源

- **[database_schema.md](database_schema.md)** - 数据库设计
  - raw_markdown 表
  - paper_leads 表
  - tender_leads 表
  - feedback 表

### 处理层
- **[file_structure.md](file_structure.md)** - 项目文件结构
  - src/ 目录结构
  - 爬虫模块
  - 提取模块
  - 批处理模块⭐

- **[error_handling.md](error_handling.md)** - 异常处理与日志
  - API 错误处理
  - 批处理错误处理⭐
  - 日志规范
  - 飞书通知

### 输出层
- **[csv_output.md](csv_output.md)** - CSV 输出规格
  - 增量导出
  - 全量导出
  - 字段说明（含中文翻译）⭐

### 评分层
- **[scoring_rules.md](scoring_rules.md)** - 评分规则
  - 7 维度评分
  - 等级映射（A/B/C/D）
  - 关键词匹配规则

### 反馈层
- **[feedback_versioning.md](feedback_versioning.md)** - 销售反馈机制
  - feedback 表结构
  - 5 个反馈维度
  - 优化流程

---

## ⭐ 最新更新（2026-03-13）

### 批处理优化
- **模型**: GLM-4-Plus（temperature: 0.1）
- **Prompt**: v2（docs/Batch Prompt v2.md）
- **格式**: 双 role 结构（system + user）
- **详见**: `architecture_overview.md` 第 4 节

### Jina Reader API 优化
- **15 个优化 Headers**（付费用户）
- **反爬虫拦截**: 60% → <10%
- **缓存**: 1 小时（提升 3-5x 速度）
- **详见**: `data_sources.md`

### 数据库字段更新
- **新增**: `address_cn`（中文翻译）
- **新增**: `all_authors_info_cn`（中文翻译）
- **详见**: `database_schema.md`

---

## 📖 阅读顺序（新成员）

1. **architecture_overview.md** - 了解整体架构
2. **data_sources.md** - 了解数据来源
3. **file_structure.md** - 了解代码结构
4. **database_schema.md** - 了解数据模型
5. **error_handling.md** - 了解异常处理
6. **csv_output.md** - 了解输出格式
7. **scoring_rules.md** - 了解评分规则

---

## 🔗 相关文档

- **实现计划**: `docs/plans/2026-03-13-jina-api-optimization.md`
- **解决方案**: `docs/solutions/2026-03-13-jina-api-optimization.md`
- **API 参数**: `docs/jina_api_parameters.md`
- **Prompt v2**: `docs/Batch Prompt v2.md`

---

**最后更新**: 2026-03-13 20:38  
**维护者**: OpenClaw Assistant
