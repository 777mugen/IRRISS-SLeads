# CSV 输出规格

## 输出周期

| 周期 | 类型 | 规则 |
|------|------|------|
| 每日 | 增量 | 仅新增和变更的线索（字段缺失补齐后） |
| 每周日 08:00 前 | 全量 | 先与数据库同步，diff 字段标注变更标记 |

---

## 论文线索 CSV 字段

| 字段名 | 说明 | 来源 |
|--------|------|------|
| DOI | DOI 标识符 | paper_leads.doi |
| 标题 | 文章标题 | paper_leads.title |
| 发表时间 | YYYY-MM-DD | paper_leads.published_at |
| 原文链接 | https://doi.org/[DOI] | paper_leads.article_url |
| 来源 | 数据来源（当前固定"PubMed"） | paper_leads.source |
| 通讯作者 | 通讯作者姓名（如有多个只写第一个） | paper_leads.name |
| 单位地址 | 通讯作者单位地址（英文原文） | paper_leads.address |
| **单位地址（中文）** | **通讯作者单位地址（中文翻译）** | **paper_leads.address_cn** |
| 联系电话 | 通讯作者电话 | paper_leads.phone |
| 电子邮箱 | 通讯作者邮箱 | paper_leads.email |
| 线索等级 | A/B/C/D | paper_leads.grade |
| 其他作者信息（英文） | 一人一行，格式：姓名,单位,邮箱,电话 | paper_leads.all_authors_info |
| **其他作者信息（中文）** | **一人一行，格式：姓名,单位中文,邮箱,电话** | **paper_leads.all_authors_info_cn** |

### 其他作者信息格式

在数据库中存储为 JSON：
```json
[
  {
    "name": "Author Name",
    "institution": "Affiliation",
    "email": "email@example.com",
    "phone": "+86-xxx-xxxx"
  }
]
```

CSV 导出时展开为多行：
```
张三,清华大学,abc@tsinghua.edu.cn,
李四,北京大学,def@pku.edu.cn,+86-138-0000-0000
王五,中科院,ghi@cas.cn,
```

---

## 招标线索 CSV 字段

（保持原有字段，不变）

| 字段名 | 说明 |
|--------|------|
| 项目名称 | - |
| 招标单位 | - |
| 姓名 | - |
| 邮箱 | - |
| 手机 | - |
| 地址 | - |
| 预算信息 | - |
| 发生时间 | - |
| 等级 | A/B/C/D |
| 来源链接 | - |

---

## 增量导出逻辑

### 触发条件

1. **新增 DOI**: DOI 不在数据库中 → 导出
2. **字段更新**: DOI 已存在，但以下字段从缺失变为有值：
   - 标题
   - 发表时间
   - 通讯作者
   - 单位地址
   - 联系电话
   - 电子邮箱

### 增量导出示例

今天有 10 条新论文入库：
- 7 条字段完整 → 导出
- 3 条字段缺失 → 不导出

明天补齐了 3 条中的 2 条：
- 2 条补齐 → 导出（作为"更新"）
- 1 条仍缺失 → 不导出

---

## 全量导出 diff 标注

每周日全量导出时，每条记录增加 `变更标记` 字段：

| 标记 | 说明 |
|------|------|
| 新增 | 本周新入库的线索 |
| 已更新 | 本周有字段变更的线索 |
| 无变化 | 与上周一致 |

---

## 输出目录

```
output/paper_leads/
  ├── paper_leads_incremental_YYYY-MM-DD.csv
  └── paper_leads_full_YYYY-MM-DD.csv

output/tender_leads/
  ├── tender_leads_incremental_YYYY-MM-DD.csv
  └── tender_leads_full_YYYY-MM-DD.csv
```

---

## 使用方式

CSV 由销售手动导入飞书多维表格，本系统不直接调用飞书 API。

---

## 注意事项

1. **线索等级 vs 分数**:
   - CSV 中只展示等级（A/B/C/D）
   - 分数（0-100）仅在数据库内部保留，用于排序和筛选
   
2. **其他作者信息**:
   - 数据库存储为 JSON 格式
   - CSV 导出时展开为一人一行
   - 不同作者之间换行分隔

3. **编码格式**:
   - UTF-8-BOM（Excel 兼容）
