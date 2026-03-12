# 智谱批量处理 API 集成计划

**创建日期**: 2026-03-13
**作者**: Assistant
**状态**: 计划中

---

## 目标

集成智谱批量处理 API 到 SLeads 系统，实现离线批量提取论文信息，替代现有的实时 API 调用方式。

---

## 背景

### 现有问题

1. **实时 API 限制**：
   - GLM-5 实时 API 有速率限制（20-30秒/请求）
   - 处理 100 篇论文需要 30-50 分钟
   - 高峰期可能出现 429 错误

2. **两阶段提取复杂**：
   - 需要先定位，再提取
   - 两次 API 调用
   - 失败率高

3. **空响应问题**：
   - GLM-5 实时 API 偶尔返回空响应
   - 影响数据完整性

### 批量 API 优势

1. **更高吞吐量**：
   - 一次提交 100+ 篇论文
   - 异步处理，不受速率限制

2. **成本更低**：
   - 批量 API 通常更便宜
   - 按实际 token 使用计费

3. **适合离线场景**：
   - 我们已存储 raw_markdown
   - 定时任务场景
   - 不需要实时响应

---

## 架构设计

### 数据流

```
raw_markdown 表（DOI + Markdown）
    ↓
BatchProcessor（构建 JSONL 文件）
    ↓
ZhiPuBatchClient（上传 + 提交）
    ↓
智谱批量处理 API（异步处理）
    ↓
结果文件（JSONL）
    ↓
BatchResultParser（解析结果）
    ↓
paper_leads 表（结构化数据）
```

### 关键组件

#### 1. BatchProcessor

**职责**：
- 从 raw_markdown 表读取未处理论文
- 构建 JSONL 请求文件
- 为每篇论文生成 custom_id（基于 DOI）

**位置**: `src/processors/batch_processor.py`

**核心方法**:
```python
class BatchProcessor:
    async def get_unprocessed_papers() -> List[RawMarkdown]
    async def build_batch_file(papers: List[RawMarkdown]) -> Path
    async def update_paper_lead(doi: str, data: dict)
```

#### 2. ZhiPuBatchClient

**职责**：
- 上传 JSONL 文件
- 创建批处理任务
- 轮询任务状态
- 下载结果文件

**位置**: `src/llm/batch_client.py`（已实现 ✅）

**核心方法**:
```python
class ZhiPuBatchClient:
    async def upload_file(file_path: Path) -> str
    async def create_batch(input_file_id: str) -> str
    async def get_batch(batch_id: str) -> dict
    async def wait_for_completion(batch_id: str) -> dict
    async def download_result(file_id: str, output_path: Path) -> Path
```

#### 3. BatchResultParser

**职责**：
- 解析结果 JSONL 文件
- 提取结构化数据
- 处理错误和失败

**位置**: `src/processors/batch_result_parser.py`

**核心方法**:
```python
class BatchResultParser:
    def parse_result_file(file_path: Path) -> List[dict]
    def validate_extraction(data: dict) -> bool
    def handle_error(error_data: dict)
```

#### 4. BatchPipeline

**职责**：
- 协调整个批量处理流程
- 提供统一的接口

**位置**: `src/pipeline_batch.py`

**核心方法**:
```python
class BatchPipeline:
    async def run_batch_extraction(limit: int = 100) -> dict
    async def check_batch_status(batch_id: str) -> dict
    async def process_batch_results(batch_id: str) -> dict
```

---

## Prompt 设计

### 关键改进

1. **不提取 References**：
   - 在 Prompt 中明确说明
   - 避免 GLM-5 提取无关信息

2. **max_tokens = 4096**：
   - 足够返回完整结构化数据
   - 有充足的安全裕度

3. **JSON 格式要求**：
   - 明确字段名称
   - 必填字段说明

### Prompt 模板

```
从以下论文内容中提取信息，以 JSON 格式返回。

**🔴 重要说明 - 必须严格遵守**：

1. **绝对不要提取 References 部分的任何信息**：
   - References 中的作者姓名、单位、联系方式
   - References 中的文章标题、DOI
   - References 中的任何其他信息
   
2. **只提取正文部分的信息**：
   - 论文标题（正文标题）
   - 发表时间
   - 通讯作者信息（正文中标注的）
   
3. **通讯作者识别标准**：
   - 寻找 "Correspondence to"、"Corresponding Author"、"通讯作者" 等标识
   - 只提取明确标注为通讯作者的人员信息
   - 不要提取其他作者或被引用文献作者的信息

4. **如果某个字段找不到，设为 null**

论文内容：
{markdown_content}

---

**返回格式（JSON）**：
{
  "title": "文章标题",
  "published_at": "YYYY-MM-DD 或 null",
  "corresponding_author": {
    "name": "通讯作者姓名（来自正文，非 References）",
    "email": "邮箱地址（来自正文，非 References）",
    "phone": "电话号码（来自正文，非 References）",
    "institution": "所属单位（来自正文，非 References）",
    "address": "单位地址（来自正文，非 References）"
  }
}

**只返回 JSON，不要有任何其他文字。**
```

---

## 数据库变更

### 1. 更新 raw_markdown 表

**新增字段**:

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| processing_status | VARCHAR(20) | 'pending' | 处理状态 |
| batch_id | VARCHAR | NULL | 批处理任务 ID |
| processed_at | TIMESTAMP | NULL | 处理完成时间 |
| error_message | TEXT | NULL | 错误信息 |

**处理状态说明**:
- `pending`: 未处理
- `processing`: 已提交到智谱，正在处理
- `completed`: 处理完成
- `failed`: 处理失败

**SQL 变更**:
```sql
ALTER TABLE raw_markdown 
ADD COLUMN processing_status VARCHAR(20) DEFAULT 'pending',
ADD COLUMN batch_id VARCHAR,
ADD COLUMN processed_at TIMESTAMP,
ADD COLUMN error_message TEXT;

CREATE INDEX idx_raw_markdown_processing_status 
ON raw_markdown(processing_status);

CREATE INDEX idx_raw_markdown_batch_id 
ON raw_markdown(batch_id);
```

### 2. 无需新增表

使用现有的 `raw_markdown` 和 `paper_leads` 表。

### 字段映射

| raw_markdown 字段 | paper_leads 字段 | 提取路径 |
|------------------|------------------|---------|
| doi | doi | 直接复制 |
| pmid | pmid | 直接复制 |
| markdown_content | title | data['title'] |
| - | published_at | data['published_at'] |
| - | name | data['corresponding_author']['name'] |
| - | email | data['corresponding_author']['email'] |
| - | phone | data['corresponding_author']['phone'] |
| - | institution | data['corresponding_author']['institution'] |
| - | address | data['corresponding_author']['address'] |

---

## 实现步骤

### Phase 1: 核心组件（2-3 小时）

- [ ] **1.0 数据库迁移**
  - 文件: `alembic/versions/add_batch_processing_fields.py`
  - 功能: 添加 processing_status、batch_id 等字段
  - 测试: 执行迁移，验证字段

- [ ] **1.1 创建 BatchProcessor**
  - 文件: `src/processors/batch_processor.py`
  - 功能: 读取未处理论文（processing_status='pending'），构建 JSONL
  - 测试: 单元测试

- [ ] **1.2 创建 BatchResultParser**
  - 文件: `src/processors/batch_result_parser.py`
  - 功能: 解析结果文件，验证数据
  - 测试: 单元测试

- [ ] **1.3 创建 BatchPipeline**
  - 文件: `src/pipeline_batch.py`
  - 功能: 协调整个流程
  - 测试: 集成测试

### Phase 2: Prompt 优化（1 小时）

- [ ] **2.1 优化提取 Prompt**
  - 文件: `src/prompts/batch_extraction.py`
  - 功能: 不提取 References
  - 测试: 手动验证

### Phase 3: 调度集成（1-2 小时）

- [ ] **3.1 添加批处理任务**
  - 文件: `src/scheduler.py`
  - 功能: 每日批量处理任务
  - 测试: 手动触发

- [ ] **3.2 添加飞书通知**
  - 文件: `src/notifiers/feishu.py`
  - 功能: 批处理完成通知
  - 测试: 发送测试

### Phase 4: 监控和错误处理（1 小时）

- [ ] **4.1 添加日志**
  - 记录批处理状态
  - 记录失败原因

- [ ] **4.2 添加重试机制**
  - 失败的论文重新提交
  - 最多重试 3 次

---

## 测试计划

### 单元测试

1. **BatchProcessor**:
   - 测试 JSONL 文件构建
   - 测试 custom_id 生成
   - 测试字段映射

2. **BatchResultParser**:
   - 测试结果解析
   - 测试错误处理
   - 测试数据验证

3. **BatchPipeline**:
   - 测试完整流程
   - 测试状态查询

### 集成测试

1. **小批量测试**（10 篇论文）：
   - 提交任务
   - 等待完成
   - 验证结果

2. **大批量测试**（100 篇论文）：
   - 提交任务
   - 等待完成
   - 验证结果

### 手动测试

1. **Prompt 效果验证**：
   - 检查 References 是否被提取
   - 检查字段完整性
   - 检查 JSON 格式

2. **错误场景测试**：
   - 无效 DOI
   - 空 Markdown
   - API 错误

---

## 部署计划

### 部署步骤

1. **合并代码到 main**：
   - 创建 PR
   - 代码审查
   - 合并

2. **运行数据库迁移**：
   - 无需迁移（使用现有表）

3. **更新环境变量**：
   - 已更新 ZAI_API_KEY ✅

4. **重启服务**：
   - 重启调度器

### 回滚计划

如果批量 API 出现问题：
1. 回退到实时 API（TwoStageExtractor）
2. 恢复代码到上一版本

---

## 风险和缓解

### 风险 1: 批量 API 处理时间长

**缓解**：
- 设置合理的等待时间（最多 2 小时）
- 添加进度通知
- 支持手动查询状态

### 风险 2: Prompt 效果不佳

**缓解**：
- 先小批量测试
- 手动验证结果
- 根据反馈优化 Prompt

### 风险 3: JSON 格式错误

**缓解**：
- 添加 JSON 验证
- 失败的论文重新提交
- 记录错误原因

---

## 成功标准

### 功能标准

- ✅ 能成功提交 100 篇论文的批处理任务
- ✅ 能正确解析结果文件
- ✅ 能更新 paper_leads 表
- ✅ 不提取 References 部分

### 性能标准

- ✅ 处理 100 篇论文在 1 小时内完成
- ✅ 提取成功率 > 80%
- ✅ JSON 格式正确率 > 95%

### 质量标准

- ✅ 有完整的单元测试
- ✅ 有详细的日志记录
- ✅ 有错误处理机制

---

## 时间估算

| 阶段 | 时间 | 说明 |
|------|------|------|
| Phase 1: 核心组件 | 2-3 小时 | 主要开发工作 |
| Phase 2: Prompt 优化 | 1 小时 | Prompt 调整 |
| Phase 3: 调度集成 | 1-2 小时 | 集成到定时任务 |
| Phase 4: 监控 | 1 小时 | 日志和重试 |
| **总计** | **5-7 小时** | |

---

## 下一步行动

1. **用户确认计划**：
   - 是否需要调整？
   - 优先级是否合理？

2. **开始实现**：
   - 创建 Phase 1 组件
   - 编写单元测试

3. **测试验证**：
   - 小批量测试
   - Prompt 效果验证

---

## 参考资料

- [智谱批量处理 API 文档](https://docs.bigmodel.cn/api-reference/批处理-api/创建批处理任务)
- [智谱对话补全 API 文档](https://docs.bigmodel.cn/api-reference/模型-api/对话补全)
- 测试批处理 ID: `batch_2032124688843411456`
- 测试文件 ID: `1773331255_8685985344ff4292a453e27862bc0885`

---

## 变更日志

| 日期 | 变更内容 | 作者 |
|------|---------|------|
| 2026-03-13 | 创建计划 | Assistant |
