---
title: "销售反馈系统：CSV 导入 + Web API + Web 界面"
category: "feedback-system"
component: "销售反馈数据管理"
severity: "medium"
resolved_at: "2026-03-16"
detected_at: "2026-03-15"
github_issue: null
related_docs:
  - docs/solutions/api-integration/paywall-content-extraction-jina-vs-zhipu.md
tags:
  - feedback
  - csv-import
  - web-api
  - sales
  - data-quality
status: "verified"
---

# 销售反馈系统：CSV 导入 + Web API + Web 界面

## Problem Symptom

**场景**: 需要收集销售对线索的反馈，用于优化评分策略

**痛点**:
- 销售反馈数据散落在邮件、Excel、微信群
- 无法与原始线索数据关联
- 缺乏标准化的反馈流程
- 无法利用反馈数据优化算法

**影响**:
- 评分策略调整依赖直觉，缺乏数据支撑
- 无法识别哪些线索质量高
- 无法学习"好线索"的特征

---

## Root Cause

**技术原因**:
1. **缺少数据模型**：没有 `feedback` 表来存储反馈
2. **缺少导入机制**：销售习惯用 Excel，没有导入脚本
3. **缺少 Web 界面**：销售不愿意学习复杂工具

**业务原因**:
1. **流程不清晰**：销售不知道如何反馈
2. **激励不足**：反馈没有直接收益
3. **反馈周期长**：从接触到反馈需要时间

---

## Solution

### Step 1: 数据模型设计

**表结构** (`src/db/models.py`):

```python
class Feedback(Base):
    """销售反馈表"""
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    paper_lead_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('paper_leads.id', ondelete='CASCADE')
    )

    # 5 个反馈维度（好/中/差）
    accuracy: Mapped[str]  # 线索准确性
    demand_match: Mapped[str]  # 需求匹配度
    contact_validity: Mapped[str]  # 联系方式有效性
    deal_speed: Mapped[str]  # 成交速度
    deal_price: Mapped[str]  # 成交价格

    notes: Mapped[str]  # 销售备注
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

**关联关系**:
```
paper_leads (1) ←→ (N) feedback
    ↓
feedback_status 更新为"已反馈"
```

---

### Step 2: CSV 导入脚本

**脚本**: `scripts/import_feedback_csv.py`

**用法**:
```bash
python scripts/import_feedback_csv.py feedback.csv
```

**CSV 格式**:
```csv
paper_lead_id,doi,线索准确性,需求匹配度,联系方式有效性,成交速度,成交价格,备注
123,10.1016/j.jad.2026.121506,好,好,中,差,中,客户很感兴趣但预算有限
```

**核心功能**:
- ✅ 支持通过 `paper_lead_id` 或 `doi` 查找线索
- ✅ 自动更新已有反馈
- ✅ 自动更新 `feedback_status` 为"已反馈"
- ✅ 统计成功/失败数量

**代码示例**:
```python
async def import_feedback_csv(csv_path: Path):
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row in reader:
            # 查找 paper_lead_id
            paper_lead_id = row.get('paper_lead_id')

            if not paper_lead_id:
                # 尝试通过 DOI 查找
                doi = row.get('doi')
                lead = await session.execute(
                    select(PaperLead.id).where(PaperLead.doi == doi)
                )
                paper_lead_id = lead.scalar_one_or_none()

            # 创建或更新反馈
            feedback = Feedback(
                paper_lead_id=paper_lead_id,
                accuracy=row['线索准确性'],
                demand_match=row['需求匹配度'],
                # ...
            )
            session.add(feedback)

            # 更新 feedback_status
            lead = await session.get(PaperLead, paper_lead_id)
            lead.feedback_status = '已反馈'
```

---

### Step 3: Web API

**文件**: `src/web/api/feedback.py`

**端点**:

#### 1. 创建/更新反馈
```http
POST /api/feedback/
Content-Type: application/json

{
  "paper_lead_id": 123,
  "accuracy": "好",
  "demand_match": "好",
  "contact_validity": "中",
  "deal_speed": "差",
  "deal_price": "中",
  "notes": "客户很感兴趣但预算有限"
}
```

**响应**:
```json
{
  "status": "success",
  "message": "反馈已创建",
  "feedback_id": 456
}
```

#### 2. 获取反馈
```http
GET /api/feedback/{paper_lead_id}
```

**响应**:
```json
{
  "status": "success",
  "feedback": {
    "id": 456,
    "paper_lead_id": 123,
    "accuracy": "好",
    "demand_match": "好",
    "contact_validity": "中",
    "deal_speed": "差",
    "deal_price": "中",
    "notes": "客户很感兴趣但预算有限",
    "created_at": "2026-03-16 00:00:00",
    "updated_at": "2026-03-16 00:00:00"
  }
}
```

---

### Step 4: Web 界面

**文件**: `src/web/templates/feedback/create.html`

**访问地址**: http://localhost:8000/feedback/create

**功能**:
1. **搜索线索**（支持 ID 和 DOI）
2. **显示线索详情**（标题、作者、邮箱、机构）
3. **录入 5 维度反馈**（下拉选择：好/中/差）
   - 线索准确性
   - 需求匹配度
   - 联系方式有效性
   - 成交速度
   - 成交价格
4. **添加销售备注**（文本框）
5. **自动加载历史反馈**（如果已存在）

**界面截图**（伪代码）:
```
┌─────────────────────────────────────────┐
│ 销售反馈录入                              │
├─────────────────────────────────────────┤
│ 查找线索                                 │
│ 线索 ID: [  123  ]  或 DOI: [  10.1016... ] │
│ [查找]                                   │
├─────────────────────────────────────────┤
│ 线索信息                                 │
│ ID: 123                                 │
│ 标题: Multiplex Immunofluorescence...   │
│ 作者: 张三                               │
│ 邮箱: zhangsan@example.com              │
├─────────────────────────────────────────┤
│ 反馈维度                                 │
│ 线索准确性: [好 ▼]                       │
│ 需求匹配度: [好 ▼]                       │
│ 联系方式有效性: [中 ▼]                   │
│ 成交速度: [差 ▼]                         │
│ 成交价格: [中 ▼]                         │
│ 备注: [客户很感兴趣但预算有限...        ] │
│ [提交反馈]  [重置]                       │
└─────────────────────────────────────────┘
```

---

## Verification

### 功能测试
```bash
# 1. 启动 Web 服务
python -m src.web.main

# 2. 访问界面
open http://localhost:8000/feedback/create

# 3. 测试 API
curl -X POST http://localhost:8000/api/feedback/ \
  -H "Content-Type: application/json" \
  -d '{"paper_lead_id": 123, "accuracy": "好", ...}'

# 4. 测试 CSV 导入
python scripts/import_feedback_csv.py test_feedback.csv
```

### 数据验证
```sql
-- 检查反馈数据
SELECT
    f.id,
    pl.doi,
    f.accuracy,
    f.demand_match,
    f.contact_validity,
    f.deal_speed,
    f.deal_price,
    f.notes
FROM feedback f
JOIN paper_leads pl ON f.paper_lead_id = pl.id
LIMIT 10;

-- 检查 feedback_status 更新
SELECT feedback_status, COUNT(*)
FROM paper_leads
GROUP BY feedback_status;
```

---

## Prevention Strategies

### 1. 反馈流程标准化

**标准流程**:
1. 销售收到线索 → 2. 联系客户 → 3. 记录结果 → 4. 录入反馈

**SLA 要求**:
- 联系后 24 小时内录入反馈
- 成交后 48 小时内补充详细信息

---

### 2. 反馈质量监控

**关键指标**:
- 反馈覆盖率 = 有反馈的线索数 / 总线索数
- 反馈及时性 = 24 小时内录入的反馈数 / 总反馈数
- 反馈完整性 = 5 个维度都填写的反馈数 / 总反馈数

**告警规则**:
```yaml
alerts:
  - name: feedback_rate_low
    condition: feedback_rate < 50%
    severity: warning
    message: "反馈覆盖率低于 50%"
```

---

### 3. 反馈数据应用

**用途**:
1. **优化评分策略**：分析"好"线索的特征，调整权重
2. **关键词优化**：分析"好"线索的关键词，更新关键词库
3. **算法训练**：用反馈数据训练分类模型

**示例分析**:
```sql
-- 分析"好"线索的特征
SELECT
    AVG(score) as avg_score,
    AVG(CASE WHEN email IS NOT NULL THEN 1 ELSE 0 END) as email_rate,
    AVG(CASE WHEN institution_cn LIKE '%医院%' THEN 1 ELSE 0 END) as hospital_rate
FROM paper_leads pl
JOIN feedback f ON pl.id = f.paper_lead_id
WHERE f.accuracy = '好' AND f.demand_match = '好';
```

---

## Related Issues & Docs

### 相关文档
- [Pipeline 来源追踪](data-pipeline/pipeline-source-tracking.md)
- [付费墙内容获取](api-integration/paywall-content-extraction-jina-vs-zhipu.md)

### 相关 PR
- PR #4: feat: 添加销售反馈系统和 Pipeline 1 修复

---

## Key Learnings

### 1. 多种导入方式并存
- **教训**: 强制销售使用单一方式会导致反馈率下降
- **经验**: 提供 CSV 导入和 Web 界面两种方式
- **行动**: 销售可以批量导出 Excel，填写后导入

### 2. 反馈维度不能太多
- **教训**: 10 个维度的反馈，销售只填前 3 个
- **经验**: 5 个核心维度是最优解
- **行动**: 精简为 5 个维度，每个都是关键指标

### 3. 反馈必须与原数据关联
- **教训**: 独立的反馈表无法追溯
- **经验**: 使用 `paper_lead_id` 外键关联
- **行动**: 自动更新 `feedback_status`，便于筛选

---

## Future Improvements

### 短期
- [ ] 反馈提醒功能（定时邮件提醒）
- [ ] 反馈统计报表（Web Dashboard）
- [ ] 批量导入优化（支持 Excel）

### 中期
- [ ] 反馈激励机制（积分、排行榜）
- [ ] 反馈质量评分（检测随意填写）
- [ ] 自动分析反馈趋势

### 长期
- [ ] 机器学习预测线索质量
- [ ] 自动调整评分策略
- [ ] A/B 测试不同策略

---

## Code References

### 关键文件
- `scripts/import_feedback_csv.py` - CSV 导入脚本
- `src/web/api/feedback.py` - Web API
- `src/web/routes/feedback.py` - 路由
- `src/web/templates/feedback/create.html` - Web 界面

### 数据库迁移
```sql
-- 创建 feedback 表
CREATE TABLE feedback (
    id SERIAL PRIMARY KEY,
    paper_lead_id INTEGER REFERENCES paper_leads(id) ON DELETE CASCADE,
    accuracy VARCHAR(10),
    demand_match VARCHAR(10),
    contact_validity VARCHAR(10),
    deal_speed VARCHAR(10),
    deal_price VARCHAR(10),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 添加索引
CREATE INDEX idx_feedback_paper_lead_id ON feedback(paper_lead_id);
```

---

## Conclusion

销售反馈系统是闭环学习的关键环节：

1. **数据收集**：CSV + Web 双渠道
2. **数据关联**：与原始线索关联
3. **数据应用**：优化评分策略

**核心价值**: 将销售的隐性知识显性化，形成可复用的数据资产。

---

**User**: 董胜豪 (ou_267c16d0bbf426921ce84255b6cfd1f9)
**Repository**: https://github.com/777mugen/IRRISS-SLeads
**Commit**: d7a9668
