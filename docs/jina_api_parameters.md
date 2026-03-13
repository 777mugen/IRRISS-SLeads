# Jina API 调用参数说明

**创建时间**: 2026-03-13 19:41

---

## 📊 两种 API 调用方式

### 1. Jina Search API（搜索）

**端点**: `https://s.jina.ai/`

**HTTP 方法**: `POST`（主要）或 `GET`（回退）

**请求头**:
```python
headers = {
    "Authorization": "Bearer {api_key}",      # API Key（如果有）
    "Content-Type": "application/json",       # 内容类型
    "Accept": "application/json",             # 接受 JSON 响应
    "X-Site": "pubmed.ncbi.nlm.nih.gov"      # 可选：限制站点
}
```

**请求体（POST）**:
```json
{
    "q": "site:pubmed.ncbi.nlm.nih.gov tumor OR cancer OR immunotherapy",
    "num": 20
}
```

**参数说明**:

| 参数 | 类型 | 必填 | 说明 | 示例值 |
|------|------|------|------|--------|
| **q** | string | ✅ | 搜索查询字符串 | `"site:pubmed.ncbi.nlm.nih.gov tumor OR cancer"` |
| **num** | integer | ❌ | 返回结果数量 | `20`（默认 10） |
| **X-Site** | header | ❌ | 限制搜索站点 | `pubmed.ncbi.nlm.nih.gov` |
| **Authorization** | header | ❌ | API Key（免费可省略） | `Bearer xxx...` |

**查询字符串格式**:
```python
query = f"site:pubmed.ncbi.nlm.nih.gov {keywords}"

# 示例
"site:pubmed.ncbi.nlm.nih.gov tumor OR cancer OR immunotherapy"
```

**响应格式**:
```json
{
    "data": [
        {
            "url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
            "title": "...",
            "description": "..."
        },
        ...
    ]
}
```

---

### 2. Jina Reader API（读取内容）

**端点**: `https://r.jina.ai/{url}`

**HTTP 方法**: `GET`

**请求头**:
```python
headers = {
    "Authorization": "Bearer {api_key}"       # API Key（如果有）
}
```

**URL 格式**:
```
https://r.jina.ai/https://pubmed.ncbi.nlm.nih.gov/12345678/
```

**参数说明**:

| 参数 | 类型 | 必填 | 说明 | 示例值 |
|------|------|------|------|--------|
| **{url}** | path | ✅ | 要读取的完整 URL（URL 编码） | `https://pubmed.ncbi.nlm.nih.gov/12345678/` |
| **Authorization** | header | ❌ | API Key（免费可省略） | `Bearer xxx...` |

**响应格式**:
```
# 论文标题

Author: Zhang Wei, Wang Xiaohong
Published: 2024-03-15
DOI: 10.1234/example.2024.001

## Abstract
This paper presents...

## Methods
...

## References
1. Smith J. et al. (2023)...
```

---

## 🔍 实际调用代码

### 搜索论文

```python
# 位置：src/crawlers/pubmed.py

async def search_urls(self, query: str, max_results: int = 100):
    # 构建搜索查询
    search_query = f"site:pubmed.ncbi.nlm.nih.gov {query}"
    
    # 调用 Jina Search
    urls = await self.jina.search(
        query=search_query,
        max_results=max_results * 2
    )
    
    return urls
```

**实际传递的参数**:
```python
query = "site:pubmed.ncbi.nlm.nih.gov tumor OR cancer OR immunotherapy"
max_results = 200
```

---

### 读取论文内容

```python
# 位置：src/crawlers/pubmed.py

async def fetch_paper(self, url: str):
    # 调用 Jina Reader
    content = await self.jina.read(url)
    
    return {
        'url': url,
        'content': content,
        'status': 'success'
    }
```

**实际传递的参数**:
```python
url = "https://pubmed.ncbi.nlm.nih.gov/12345678/"
```

---

## 📋 JinaClient 完整实现

```python
# 位置：src/crawlers/jina_client.py

class JinaClient:
    READER_URL = "https://r.jina.ai"
    SEARCH_URL = "https://s.jina.ai"
    
    def __init__(self, api_key: Optional[str] = None):
        # 初始化 API Key（从配置或参数）
        self.api_key = api_key or config.jina_api_key
        
        # 设置请求头
        self.headers = {}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
        
        # 初始化 HTTP 客户端
        self._client = httpx.AsyncClient(
            timeout=30.0,           # 超时时间：30秒
            follow_redirects=True   # 自动跟随重定向
        )
    
    async def search(self, query: str, max_results: int = 10, site: str = None):
        """搜索 API"""
        url = f"{self.SEARCH_URL}/"
        
        # 请求体
        payload = {
            "q": query,
            "num": max_results
        }
        
        # 请求头
        headers = {
            **self.headers,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # 可选：限制站点
        if site:
            headers["X-Site"] = site
        
        # 发送 POST 请求
        response = await self._client.post(
            url,
            headers=headers,
            json=payload
        )
        
        # 如果失败，回退到 GET
        if response.status_code != 200:
            get_url = f"{self.SEARCH_URL}/{query}"
            get_headers = {**self.headers, "Accept": "application/json"}
            if site:
                get_headers["X-Site"] = site
            
            response = await self._client.get(get_url, headers=get_headers)
        
        # 解析响应
        return self._parse_urls(response)
    
    async def read(self, url: str):
        """读取 API"""
        reader_url = f"{self.READER_URL}/{url}"
        
        response = await self._client.get(
            reader_url,
            headers=self.headers
        )
        response.raise_for_status()
        
        return response.text
```

---

## 🎯 关键参数解释

### Search API 参数

1. **q（查询字符串）**
   - **作用**: 搜索关键词
   - **格式**: `site:域名 关键词1 OR 关键词2 OR 关键词3`
   - **示例**: `"site:pubmed.ncbi.nlm.nih.gov tumor OR cancer"`
   - **说明**: `site:` 限制搜索范围，`OR` 连接多个关键词

2. **num（结果数量）**
   - **作用**: 返回的结果数量
   - **默认值**: 10
   - **建议值**: 20-100
   - **说明**: 实际返回可能少于请求值

3. **X-Site（站点限制）**
   - **作用**: 限制搜索到特定站点
   - **示例**: `pubmed.ncbi.nlm.nih.gov`
   - **说明**: 可选，也可以在 `q` 中使用 `site:` 语法

4. **Authorization（认证）**
   - **作用**: API Key 认证
   - **格式**: `Bearer {api_key}`
   - **说明**: 免费用户可省略，有更高配额

---

### Reader API 参数

1. **url（网页 URL）**
   - **作用**: 要读取的网页地址
   - **格式**: 完整 URL（需要 URL 编码）
   - **示例**: `https://pubmed.ncbi.nlm.nih.gov/12345678/`
   - **说明**: Jina 会自动解析并返回 Markdown 格式

2. **Authorization（认证）**
   - **作用**: API Key 认证
   - **格式**: `Bearer {api_key}`
   - **说明**: 免费用户可省略

---

## 🚨 常见问题

### 1. 为什么使用 `max_results * 2`？

```python
urls = await self.jina.search(search_query, max_results * 2)
```

**原因**: 
- Search API 返回的结果可能包含非论文页面
- 需要额外结果用于过滤
- 过滤后只保留纯 PMID 的论文页面

---

### 2. 为什么有 POST 和 GET 两种方式？

**原因**:
- POST 方式更标准，支持 JSON 请求体
- 如果 POST 失败（如旧版本 API），回退到 GET
- GET 方式将参数放在 URL 中

---

### 3. 超时时间为什么是 30 秒？

```python
self._client = httpx.AsyncClient(timeout=30.0, ...)
```

**原因**:
- 读取大型网页可能需要较长时间
- 30 秒是合理的平衡点
- 避免长时间阻塞

---

### 4. 免费用户有限制吗？

**免费用户**:
- ✅ 可以使用 Search 和 Reader API
- ✅ 无需 API Key
- ❌ 有配额限制（具体见官方文档）
- ❌ 可能有速率限制

**付费用户**:
- ✅ 更高配额
- ✅ 更快响应
- ✅ 优先级支持

---

## 📊 使用统计

**当前项目使用情况**:
- Search API: 获取 20 篇论文 URL
- Reader API: 读取 20 篇论文内容
- 平均每篇论文: 50-100 KB Markdown
- 总数据量: ~1.5 MB

---

## 🔗 官方文档

- **Jina Reader**: https://jina.ai/reader/
- **Jina Search**: https://jina.ai/search/
- **API 文档**: https://docs.jina.ai/

---

## ✅ 总结

**Search API**:
- 端点: `https://s.jina.ai/`
- 主要参数: `q`（查询）、`num`（数量）
- 用途: 搜索 PubMed 论文 URL

**Reader API**:
- 端点: `https://r.jina.ai/{url}`
- 主要参数: `url`（网页地址）
- 用途: 读取论文 Markdown 内容

**认证**:
- 免费用户: 无需 API Key
- 付费用户: `Authorization: Bearer {api_key}`
