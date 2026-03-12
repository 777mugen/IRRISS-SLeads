# 项目文件结构

leads-discovery/

config/
keywords.yaml
sources.yaml
scoring_paper.yaml
scoring_tender.yaml
scheduler.yaml

src/
crawlers/
extractors/
processors/
scoring/
exporters/
feedback/
versioning/
db/
scheduler/

tests/

feedback/

logs/

output/
paper_leads/
tender_leads/

.env
.env.example
.gitignore
requirements.txt
CLAUDE.md
README.md

## 模块职责

config
运行配置

crawlers
抓取数据源

extractors
LLM 字段提取

processors
去重、标准化、补齐

scoring
评分引擎

exporters
CSV 导出

feedback
反馈数据处理

versioning
策略版本管理

db
数据库模型与迁移

scheduler
定时任务
