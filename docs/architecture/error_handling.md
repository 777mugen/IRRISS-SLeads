# 异常处理与日志规范

## 异常处理

网站不可用 / 超时 → 重试 1 次
验证码 → 立即通知 shane，不自动处理
失败数据 → 当日不入库，次日重试（status=pending_retry）
外部 API 失败 → try/except 记录日志后继续
单条数据失败 → 不中断整体任务

## 日志

使用 Python logging
日志目录 logs/
级别 DEBUG / INFO / WARNING / ERROR
保留 30 天

## 通知（后续）

每日任务完成 → 飞书机器人
异常 / 验证码 → 飞书机器人
MVP 阶段 → 仅日志
