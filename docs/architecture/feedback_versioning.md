# 销售反馈机制

## 反馈表 (feedback)

销售可通过反馈表记录每条线索的实际使用情况。

### 表结构

```sql
CREATE TABLE feedback (
    id SERIAL PRIMARY KEY,
    paper_lead_id INTEGER REFERENCES paper_leads(id) ON DELETE CASCADE,
    
    -- 5个反馈维度（好/中/差）
    accuracy VARCHAR(10),           -- 线索准确性（信息是否正确）
    demand_match VARCHAR(10),       -- 需求匹配度（客户是否真有需求）
    contact_validity VARCHAR(10),   -- 联系方式有效性（能否联系到人）
    deal_speed VARCHAR(10),         -- 成交速度（从接触到成交的周期）
    deal_price VARCHAR(10),         -- 成交价格（成交金额）
    
    notes TEXT,                     -- 销售备注
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 反馈维度说明

| 字段 | 说明 | 值选项 |
|------|------|--------|
| accuracy | 线索准确性 | 好/中/差 |
| demand_match | 需求匹配度 | 好/中/差 |
| contact_validity | 联系方式有效性 | 好/中/差 |
| deal_speed | 成交速度 | 好/中/差 |
| deal_price | 成交价格 | 好/中/差 |

### 使用流程

1. 销售在飞书多维表格中填入反馈（好/中/差）
2. 定期导出反馈数据
3. 系统分析反馈数据，生成优化建议报告
4. shane 审核后确认执行
5. 执行后生成新策略版本

## 注意事项

- 反馈数据不影响已有线索的评分
- 反馈数据用于优化未来的评分策略
- 反馈数据与 paper_leads 通过外键关联
- 删除线索时，关联的反馈也会被删除（ON DELETE CASCADE）
