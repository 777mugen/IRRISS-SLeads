# 数据源与关键词配置

## 论文数据源（类型 A）

### 数据获取流程

```
关键词搜索 → PubMed Entrez API → PMID列表 → NCBI ID Converter → DOI列表 → Jina Reader → Markdown
```

### API 说明

#### 1. PubMed Entrez API
- **用途**: 关键词搜索，获取 PMID 列表
- **官方文档**: https://www.ncbi.nlm.nih.gov/books/NBK25500/
- **限制**: 3 requests/second (无 API Key)
- **参数**:
  - email: Shane@irriss.com
  - tool: IRRISS-SLeads
  - db: pubmed
  - term: 搜索关键词

#### 2. NCBI ID Converter API
- **用途**: 批量转换 PMID → DOI
- **官方文档**: https://www.ncbi.nlm.nih.gov/pmc/tools/id-converter-api/
- **优势**: 最快、最准确的 DOI 转换工具
- **格式**: JSON

#### 3. Jina Reader API
- **用途**: 通过 DOI 链接获取 Markdown 内容
- **URL格式**: https://r.jina.ai/https://doi.org/[DOI]
- **处理**: 剔除广告、侧边栏、脚本 → 干净 Markdown

### 优先级

| 优先级 | 步骤 | API |
|--------|------|-----|
| 1 | 关键词搜索 | PubMed Entrez (esearch.fcgi) |
| 2 | 获取详情 | PubMed Entrez (efetch.fcgi) |
| 3 | PMID → DOI | NCBI ID Converter API |
| 4 | 获取全文 | Jina Reader API |

时间范围：2024 年 1 月至今

## 招标数据源（类型 B）

| 优先级 | 数据源 | URL |
|--------|--------|-----|
| 1 | 中国政府采购网 | http://www.ccgp.gov.cn |
| 2 | 全国公共资源交易平台 | http://www.ggzy.gov.cn |
| 3 | 北京市政府采购网 | https://czj.beijing.gov.cn/zfcg/ |
| 4 | 上海市政府采购网 | https://www.zfcg.sh.gov.cn |
| 5 | 广东省政府采购网 | https://gdgpo.czt.gd.gov.cn |
| 6 | 江苏省政府采购网 | http://www.ccgp-jiangsu.gov.cn |
| 7 | 浙江省政府采购网 | https://zfcg.czt.zj.gov.cn |
| 8 | 中国招标投标公共服务平台 | http://www.cebpubservice.com |

## 关键词配置

关键词在运行时从 `config/keywords.yaml` 读取。

### 英文关键词
Multiplex Immunofluorescence
Immunofluorescence
Tyramide Signal Amplification
Cyclic Immunofluorescence
CODEX
Spatial Proteomics
Spatial Transcriptomics
Tissue Imaging
Fluorescence Microscopy
Autofluorescence Quenching
H&E staining

### 中文关键词
多重免疫荧光
免疫荧光
荧光淬灭
自发荧光
组织成像
空间蛋白组学
空间转录组学
HE染色
