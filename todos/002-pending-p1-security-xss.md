---
status: complete
priority: p1
issue_id: 002
tags: [security, xss, javascript, p1, code-review]
dependencies: []
created: 2026-03-15
completed: 2026-03-15
---

# P1: 修复 XSS 跨站脚本漏洞

## Problem Statement

多个模板文件存在 XSS（跨站脚本）漏洞。用户输入的数据（DOI、论文标题、邮箱、机构名称、错误信息）直接插入到 HTML 中，未经任何过滤或转义。

攻击者可以注入恶意 JavaScript 代码，窃取用户会话、cookie 或执行恶意操作。

## Findings

### 受影响的文件和位置：

1. **`src/web/templates/query/search.html:57-90`**
   - DOI、作者名、邮箱、机构未转义
   ```javascript
   <td>${r.doi}</td>  // 危险！
   <td>${paperLead?.name || '-'}</td>  // 危险！
   <td>${paperLead?.email || '-'}</td>  // 危险！
   ```

2. **`src/web/templates/batch/monitor.html:50-77`**
   - DOI 和错误信息未转义
   ```javascript
   <td>${p.doi}</td>  // 危险！
   <td>${p.error || '未知错误'}</td>  // 危险！
   ```

3. **`src/web/templates/export/index.html:158`**
   - CSV 中的 DOI 未转义

4. **`src/web/templates/analysis/stats.html:101-105`**
   - 机构名称未转义

### XSS 攻击示例：

如果 DOI 字段包含：
```
10.1234/<script>alert('XSS')</script>
```

当前代码会执行恶意脚本。

## Proposed Solutions

### Solution 1: 使用 textContent 代替 innerHTML (推荐)

**优点**:
- 自动转义 HTML 特殊字符
- 性能更好
- 标准做法

**缺点**:
- 需要修改所有模板渲染逻辑

**工作量**: 3-4 小时

**风险**: 低

**实现步骤**:
1. 将所有 `innerHTML` 改为创建 DOM 元素并设置 `textContent`
2. 修改所有模板文件（4 个文件）
3. 测试所有页面

**示例代码**:
```javascript
// 错误的方式（当前）:
td.innerHTML = `${r.doi}`;

// 正确的方式:
td.textContent = r.doi;
```

### Solution 2: 使用 HTML 转义函数

**优点**:
- 保留 innerHTML 的灵活性
- 可以选择性转义

**缺点**:
- 容易遗漏某些字段
- 维护成本高

**工作量**: 2-3 小时

**风险**: 中（可能遗漏）

**实现步骤**:
1. 创建转义函数
2. 在所有插值处应用转义
3. 代码审查确保无遗漏

**示例代码**:
```javascript
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

td.innerHTML = escapeHtml(r.doi);
```

### Solution 3: 使用 DOMPurify 库

**优点**:
- 专业库，功能全面
- 处理更多边界情况
- 持续更新

**缺点**:
- 引入外部依赖
- 增加页面加载时间

**工作量**: 2 小时

**风险**: 低

**实现步骤**:
1. 添加 DOMPurify CDN
2. 替换所有 innerHTML 为 `DOMPurify.sanitize()`

**示例代码**:
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/dompurify/3.0.6/purify.min.js"></script>
<script>
    td.innerHTML = DOMPurify.sanitize(r.doi);
</script>
```

## Recommended Action

**采用 Solution 1 (textContent)**

原因：
1. 最安全，自动转义
2. 性能最好
3. 符合最佳实践
4. 无需额外依赖

## Technical Details

**受影响文件**:
- `src/web/templates/query/search.html` (34 行代码)
- `src/web/templates/batch/monitor.html` (28 行代码)
- `src/web/templates/export/index.html` (1 行代码)
- `src/web/templates/analysis/stats.html` (5 行代码)

**总计**: 约 68 行需要修改

**修改模式**:
```javascript
// 之前:
element.innerHTML = `${variable}`;

// 之后:
element.textContent = variable;
```

## Acceptance Criteria

- [ ] 所有用户输入数据使用 `textContent` 渲染
- [ ] 测试用例：DOI 包含 `<script>` 标签不会执行
- [ ] 测试用例：论文标题包含 HTML 不会渲染
- [ ] 测试用例：邮箱包含特殊字符正确显示
- [ ] 所有模板文件审查通过
- [ ] 无 XSS 漏洞（使用 OWASP ZAP 扫描）

## Work Log

### 2026-03-15
- Security Review 发现 4 个模板文件存在 XSS 漏洞
- 优先级：P1（关键安全漏洞）
- 状态：待修复

## Resources

- OWASP XSS Prevention: https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html
- MDN textContent: https://developer.mozilla.org/en-US/docs/Web/API/Node/textContent
- DOMPurify: https://github.com/cure53/DOMPurify
