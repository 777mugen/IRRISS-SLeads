---
status: pending
priority: p1
issue_id: 001
tags: [security, authentication, p1, code-review]
dependencies: []
created: 2026-03-15
---

# P1: 实现认证/授权机制

## Problem Statement

Web Dashboard 完全没有认证或授权机制。任何有网络访问权限的人都可以：
- 查看所有论文线索和个人信息（姓名、邮箱、电话、地址）
- 通过 `/api/export/csv/full` 导出所有数据
- 通过 `/api/import/csv/confirm` 导入恶意数据
- 修改配置

**这是严重的安全漏洞，必须在生产部署前修复。**

## Findings

### Security Review 发现：
- **文件**: 所有 `src/web/` 文件
- **问题**: 整个 Web 应用没有认证或授权
- **影响**: 
  - 数据泄露风险（个人信息暴露）
  - 数据篡改风险（任何人都可以导入数据）
  - 合规风险（GDPR、数据保护法）

### Current Code:
```python
# src/web/main.py
# No authentication middleware
# No authorization checks
# All endpoints are publicly accessible
```

## Proposed Solutions

### Solution 1: OAuth2 + JWT (推荐)
**优点**:
- 行业标准，安全性高
- 支持第三方登录（Google、GitHub）
- Token 可过期和刷新
- 易于扩展到微服务架构

**缺点**:
- 实现复杂度中等
- 需要外部 OAuth 提供商或自建

**工作量**: 2-3 天

**风险**: 低

**实现步骤**:
1. 添加 `fastapi-security` 和 `python-jose` 依赖
2. 创建 `src/web/auth/` 模块
3. 实现 JWT token 生成和验证
4. 添加 `get_current_user` 依赖注入
5. 保护所有 API 端点
6. 添加登录页面

### Solution 2: Basic Auth + API Keys
**优点**:
- 实现简单快速
- 适合内部工具
- 无需外部依赖

**缺点**:
- 安全性较低
- 用户体验差
- 不适合生产环境

**工作量**: 4-6 小时

**风险**: 中（安全性不足）

**实现步骤**:
1. 添加 `HTTPBasicAuth` 中间件
2. 创建用户配置文件
3. 保护所有端点

### Solution 3: SSO 集成（企业环境）
**优点**:
- 与现有企业系统集成
- 集中管理用户
- 单点登录体验

**缺点**:
- 需要企业 SSO 基础设施
- 配置复杂

**工作量**: 3-5 天

**风险**: 中（依赖外部系统）

## Recommended Action

**采用 Solution 1 (OAuth2 + JWT)**

原因：
1. 内部工具可先用简单 JWT
2. 未来可扩展到 OAuth 提供商
3. 安全性和可维护性最佳平衡

## Technical Details

**受影响文件**:
- `src/web/main.py` - 添加认证中间件
- `src/web/api/*.py` - 所有 API 端点添加依赖注入
- `src/web/routes/*.py` - 所有路由添加认证检查
- 新增: `src/web/auth/*.py`
- 新增: `src/web/models/user.py`

**数据库变更**:
- 新增 `users` 表（存储用户信息）
- 可选：`api_keys` 表（用于程序化访问）

## Acceptance Criteria

- [ ] 未认证用户无法访问任何 API 端点
- [ ] 未认证用户无法访问 Dashboard 页面
- [ ] JWT token 正确生成和验证
- [ ] Token 过期后自动刷新
- [ ] 用户信息存储在数据库中
- [ ] 密码使用 bcrypt 加密存储
- [ ] 所有测试通过
- [ ] 安全测试通过（无认证绕过）

## Work Log

### 2026-03-15
- 初始发现：Security Review 确认无认证机制
- 优先级：P1（关键安全漏洞）
- 状态：待实施

## Resources

- FastAPI Security: https://fastapi.tiangolo.com/tutorial/security/
- OAuth2 with FastAPI: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
- JWT Best Practices: https://datatracker.ietf.org/doc/html/rfc8725
