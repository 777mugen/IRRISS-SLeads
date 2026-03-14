# 任务
从论文中提取作者联系方式，以 JSON 格式返回。

## 核心规则

### 1. 作者符号
- 数字（1, 2, 3）：机构编号
- *：通讯作者
- # 或 †：共同第一作者

示例：
- Wenhao Xu 3,# → 该作者来自第3机构，且是共同第一作者
- Tao Li 3,4,* → 该作者同时来自第3和第4机构，且是通讯作者
- Wei Zhao 1,3,* → 该作者同时来自第1和第3机构，且也是通讯作者

### 2. 通讯作者识别（优先级）
1. 标注 * 的作者（中国作者优先）
2. 第一个中国作者
3. 第一作者（作者列表中排名第一的人）

### 3. 中国作者识别
- 姓名：中文拼音（1-4 部分，首字母大写）
- 地址：包含 "china" 关键词（不区分大小写）
- 同时满足两者

### 4. 地址格式
- `address`：英文原文，多机构换行（\n）
- `address_cn`：中文翻译，多机构换行（\n）
- 格式：科室 → 机构 → 城市 → 邮编 → 国家

---

## 输出格式（JSON）

```json
{
  "title": "文章完整标题",
  "published_at": "YYYY-MM-DD 或 null",
  "doi": "https://doi.org/xxxxx 或 null",
  "corresponding_author": {
    "name": "通讯作者姓名",
    "email": "邮箱（未找到填 null）",
    "phone": "电话（未找到填 null）",
    "address": "英文地址（多机构换行）",
    "address_cn": "中文翻译（多机构换行）"
  },
  "all_authors_info": [
    {
      "name": "作者姓名 + 符号（如 Tao Li *）",
      "address": "英文地址（多机构用中文分号；分隔）",
      "email": "邮箱（非通讯作者通常留空）",
      "phone": "电话（非通讯作者通常留空）"
    }
  ],
  "all_authors_info_cn": [
    {
      "name": "作者姓名 + 符号",
      "address": "中文翻译（多机构用中文分号；分隔）",
      "email": "",
      "phone": ""
    }
  ]
}
```

---

## 完整示例

**输入作者列表**：
```
Weiping Yang 1,#, Wei Xiao 2,#, Wenhao Xu 3,#, Lijun Ren 1, Tao Li 3,4,*, Wei Zhao 1,3,*
```

**机构列表**：
```
1. School of Basic Medical Sciences, Ningxia Medical University, Yinchuan, China
2. Department of Pediatrics, General Hospital of Ningxia Medical University, Yinchuan, China
3. Ningxia Key Laboratory for Prevention of Common Infectious Diseases, Yinchuan, China
4. Department of Hepatobiliary Surgery, General Hospital of Ningxia Medical University, Yinchuan, China
```

**脚注**：
```
# These authors contributed equally to this work
* Corresponding author: taoli@email.com
```

**输出**：

```json
{
  "title": "示例论文标题",
  "published_at": "2024-03-01",
  "doi": "https://doi.org/10.1234/example",
  "corresponding_author": {
    "name": "Tao Li",
    "email": "taoli@email.com",
    "phone": null,
    "address": "Ningxia Key Laboratory for Prevention of Common Infectious Diseases, Yinchuan, China\nDepartment of Hepatobiliary Surgery, General Hospital of Ningxia Medical University, Yinchuan, China",
    "address_cn": "宁夏常见传染病防治重点实验室，银川，中国\n宁夏医科大学总医院肝胆外科，银川，中国"
  },
  "all_authors_info": [
    {
      "name": "Weiping Yang #",
      "address": "School of Basic Medical Sciences, Ningxia Medical University, Yinchuan, China",
      "email": "",
      "phone": ""
    },
    {
      "name": "Wei Xiao #",
      "address": "Department of Pediatrics, General Hospital of Ningxia Medical University, Yinchuan, China",
      "email": "",
      "phone": ""
    },
    {
      "name": "Wenhao Xu #",
      "address": "Ningxia Key Laboratory for Prevention of Common Infectious Diseases, Yinchuan, China",
      "email": "",
      "phone": ""
    },
    {
      "name": "Lijun Ren",
      "address": "School of Basic Medical Sciences, Ningxia Medical University, Yinchuan, China",
      "email": "",
      "phone": ""
    },
    {
      "name": "Tao Li *",
      "address": "Ningxia Key Laboratory for Prevention of Common Infectious Diseases, Yinchuan, China；Department of Hepatobiliary Surgery, General Hospital of Ningxia Medical University, Yinchuan, China",
      "email": "taoli@email.com",
      "phone": ""
    },
    {
      "name": "Wei Zhao *",
      "address": "School of Basic Medical Sciences, Ningxia Medical University, Yinchuan, China；Ningxia Key Laboratory for Prevention of Common Infectious Diseases, Yinchuan, China",
      "email": "",
      "phone": ""
    }
  ],
  "all_authors_info_cn": [
    {
      "name": "Weiping Yang #",
      "address": "宁夏医科大学基础医学院，银川，中国",
      "email": "",
      "phone": ""
    },
    {
      "name": "Wei Xiao #",
      "address": "宁夏医科大学总医院儿科，银川，中国",
      "email": "",
      "phone": ""
    },
    {
      "name": "Wenhao Xu #",
      "address": "宁夏常见传染病防治重点实验室，银川，中国",
      "email": "",
      "phone": ""
    },
    {
      "name": "Lijun Ren",
      "address": "宁夏医科大学基础医学院，银川，中国",
      "email": "",
      "phone": ""
    },
    {
      "name": "Tao Li *",
      "address": "宁夏常见传染病防治重点实验室，银川，中国；宁夏医科大学总医院肝胆外科，银川，中国",
      "email": "taoli@email.com",
      "phone": ""
    },
    {
      "name": "Wei Zhao *",
      "address": "宁夏医科大学基础医学院，银川，中国；宁夏常见传染病防治重点实验室，银川，中国",
      "email": "",
      "phone": ""
    }
  ]
}
```

---

# 论文内容

{content}
