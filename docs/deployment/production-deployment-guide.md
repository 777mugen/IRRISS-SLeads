# 生产部署指南

**部署日期**: 2026-03-14
**版本**: V1 Batch Extraction Strategy
**验证状态**: 100% 准确率（5/5篇验证通过）

---

## 📋 部署前检查

### 1. 代码准备

- ✅ 分支已合并到 main
- ✅ 测试数据已清理
- ✅ 工作树干净
- ⏳ 等待推送到远程（网络问题）

### 2. 环境变量

确保 `.env` 文件包含以下配置：

```bash
# Database
DATABASE_URL=postgresql+asyncpg://localhost/sleads_dev

# API Keys
JINA_API_KEY=your_jina_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ZHIPU_API_KEY=your_zhipu_api_key_here

# Scheduling
SCHEDULE_HOUR=6
SCHEDULE_MINUTE=0

# Logging
LOG_LEVEL=INFO
LOG_RETENTION_DAYS=30
```

### 3. 数据库迁移

```bash
# 检查当前版本
alembic current

# 升级到最新版本
alembic upgrade head

# 确认迁移成功
alembic history
```

---

## 🚀 部署步骤

### Step 1: 推送代码到远程

```bash
# 推送到 main 分支
git push origin main

# 确认推送成功
git status
```

### Step 2: 服务器端部署

```bash
# SSH 登录到服务器
ssh user@your-server

# 进入项目目录
cd /path/to/IRRISS-SLeads

# 拉取最新代码
git pull origin main

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行数据库迁移
alembic upgrade head

# 重启服务
systemctl restart sleads  # 或者使用你的服务管理方式
```

### Step 3: 验证部署

```bash
# 检查服务状态
systemctl status sleads

# 查看日志
tail -f logs/sleads.log

# 运行健康检查
curl http://localhost:8000/health
```

---

## 📊 V1 策略配置

### 核心配置（已内置）

- ✅ **不截断内容**: 保留完整论文内容
- ✅ **长 Prompt**: 6,676 字符，详细提取规则
- ✅ **准确性优先**: 符合项目核心原则

### 性能指标

- ✅ **批处理成功率**: 95.8%（46/48篇）
- ✅ **完整信息提取**: 39.1%（18/46篇）
- ✅ **验证准确率**: 100%（5/5篇）

---

## 🔧 运维指南

### 日常监控

```bash
# 查看批处理任务状态
python scripts/monitor_batch.py

# 检查日志
tail -f logs/batch_processing.log

# 查看数据库状态
python scripts/check_db_status.py
```

### 常见问题

#### 1. 网络问题

**症状**: Jina API 或智谱 API 超时

**解决**:
```bash
# 检查网络连接
ping jina.ai
ping open.bigmodel.cn

# 检查 API 密钥
curl -H "Authorization: Bearer $JINA_API_KEY" https://api.jina.ai/v1/models
```

#### 2. 数据库迁移失败

**症状**: `alembic upgrade head` 报错

**解决**:
```bash
# 检查数据库连接
psql -h localhost -U postgres -d sleads_dev

# 手动标记迁移版本
alembic stamp head
```

#### 3. 批处理任务失败

**症状**: 批处理任务状态为 `failed`

**解决**:
```bash
# 查看错误详情
python scripts/check_batch_status.py <batch_id>

# 重新提交任务
python scripts/resubmit_batch.py <batch_id>
```

---

## 📞 支持

- **文档**: `docs/` 目录
- **策略文档**: `docs/solutions/integration-issues/metadata-extraction-batch-api-strategy.md`
- **工作记录**: `memory/2026-03-14.md`
- **问题反馈**: GitHub Issues

---

## ✅ 部署确认清单

- [ ] 代码已推送到远程
- [ ] 服务器已拉取最新代码
- [ ] 依赖已安装
- [ ] 数据库迁移已完成
- [ ] 环境变量已配置
- [ ] 服务已重启
- [ ] 健康检查通过
- [ ] 日志正常

---

**部署完成后，V1 批处理提取策略将正式投入生产使用！** 🎉
