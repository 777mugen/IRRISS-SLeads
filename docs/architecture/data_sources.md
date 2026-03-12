# 数据源与关键词配置

## 论文数据源（类型 A）

| 优先级 | 数据源 | 说明 |
|--------|--------|------|
| 1 | PubMed / PMC | 主力来源，优先通过 Jina Reader 读取真实页面 |
| 2 | single-cell-papers | https://single-cell-papers.bioinfo-assist.com |
| 3 | OpenAlex | 补充来源 |
| 4 | CNKI | 本期暂不接入 |

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
