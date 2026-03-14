# 任务
从以下论文内容中提取信息，以 JSON 格式返回。

## 严格遵守规则：绝对不要提取 References 和 Cite This Article 部分的任何信息：

- References 和 Cite This Article 中的作者姓名、单位、联系方式
- References 和 Cite This Article 中的文章标题、DOI
- References 和 Cite This Article 中的任何其他信息
- 只提取正文内容（References 和 Cite This Article 之前的部分）


## 发表日期
提取 Issue published 或 Published Time 对应的日期。如果论文同时存在 Received、Accepted、Published 等多个日期，只取发表日期，其他日期忽略。


## DOI
提取论文的 DOI，统一使用完整 URL 格式，例如 https://doi.org/10.1234/xxx。如果原文只有编号形式如 10.1234/xxx，则补全为 https://doi.org/10.1234/xxx。


## 作者与符号规则

作者列表通常位于标题下方，例如：
Weiping Yang 1,#, Wei Xiao 2,#, Wenhao Xu 3,#, Lijun Ren 1, Xian Li 1, Junhua Yu 1, Ronghua Wang 4*

符号含义如下：

数字上标表示作者所属机构编号，对应文末的机构列表。一个作者如果同时属于多个机构，就会有多个数字，比如 3,4。# 和 † 都表示共同第一作者，意味着这几位作者对论文贡献相同，并列第一，两者含义相同，不同期刊用法不同。* 表示通讯作者，负责与期刊沟通以及接收读者问询，通常是导师或负责人。以上符号可以同时出现在一个作者名字后面。

示例：

Wenhao Xu 3,# 表示该作者来自第3机构，且是共同第一作者。

Tao Li 3,4,* 表示该作者同时来自第3和第4机构，且是通讯作者。

Wei Zhao 1,3,* 表示该作者同时来自第1和第3机构，且也是通讯作者，与 Tao Li 并列通讯作者。

Wang Fang 1,#,* 表示该作者来自第1机构，同时是共同第一作者，也是通讯作者，一个人身兼两个角色。

### 脚注说明
所有符号的具体含义以论文脚注说明为准。脚注通常没有标题，直接列出符号对应的说明文字，位置一般紧跟在作者姓名和机构列表的下方，内容通常如下：
- # These authors contributed equally to this work
- † These authors have contributed equally to this work
- * Corresponding author: email@xxx.com

通讯作者的邮箱也可能出现在文末的 Correspondence、Contact 或 *Correspondence 区域，而不是作者列表下方的脚注，需要一并查找。如果邮箱字段存在但内容为空，同样填 null。

如果脚注缺失或格式不标准，按照以下降级处理：* 默认视为通讯作者，# 和 † 默认视为共同第一作者，数字上标默认对应机构编号。如果论文完全没有任何符号标注，所有作者共享同一机构地址，则联系人取作者列表中排名第一的作者。


## 地址
机构和地理地址合并在同一字段中。地址编号与作者名称后的数字上标关联对应。例如 Lijun Ren 1，他的地址信息对应：1 Department of Breast and Thyroid Surgery, Qingdao Chengyang People's Hospital, Qingdao, 266109, China。

如果机构名称中含有斜杠，如 Rudong People's Hospital/Affiliated Rudong Hospital of Xinglin College，斜杠表示同一机构的两种称呼或并列名称，翻译时保留斜杠结构，不拆分为两个地址。


## 联系人识别规则

优先提取通讯作者，通讯作者通常用 * 标注。如果有多位通讯作者，提取排名第一的那位，例如 Jike Song 1,4* 和 Hongsheng Bi 1,2,3,4* 并列通讯作者，则提取排名靠前的 Jike Song。如果论文中没有通讯作者，则提取第一作者，第一作者是作者列表中排名第一的人。如果第一作者有多人（即共同第一作者，用 # 或 † 标注），则提取其中排名第一的那位。如果论文既没有通讯作者标注也没有第一作者信息，或者论文没有任何符号标注，则默认提取作者列表中的第一个人。


## 中国作者识别规则

**A. 姓名判断（中文拼音规则）**：支持复姓。

**B. 地址判断（中国机构）**：地址字段包含关键词 china（不区分大小写）。

**C. 组合判断规则**：同时满足姓名符合中文拼音规则且地址包含中国关键词，视为中国作者。

**D. 排除规则**：地址同时包含 "USA"、"UK"、"Japan" 等其他国家关键词以及 "China"，仍视为中国（如 "China-USA 联合研究所"）。


## 字段对应关系
corresponding_author 下的 address、email、phone 必须对应联系人这个人，不是其他作者的信息。


## 翻译要求

把 address 字段翻译并放到 address_cn 字段。每个完整地址的格式从科室→机构→城市→邮编→国家。所有地址均需翻译，包括非中国机构（如美国、日本等）也需翻译成中文。

示例：
- 四川大学华西医院心内科，成都 610041，中国
- 四川省人民医院心内科，成都 610072，中国


## 返回格式（JSON）

```json
{
  "title": "文章完整标题，主标题和副标题用冒号合并为一个字符串，来自正文非 References 部分",
  "published_at": "YYYY-MM-DD 或 null",
  "doi": "https://doi.org/xxxxx 或 null",
  "corresponding_author": {
    "name": "联系人姓名，按联系人识别规则提取",
    "email": "联系人的邮箱，找不到填 null",
    "phone": "联系人的电话，原样保留，找不到填 null",
    "address": "联系人的地址英文原文，该作者有多个机构时每个地址换行，找不到填 null",
    "address_cn": "联系人的地址中文翻译，该作者有多个机构时每个地址换行，找不到填 null"
  },
  "all_authors_info": [
    {
      "name": "作者姓名，保留英文拼音原样，并在姓名后附上该作者原本的符号标记，如 Weiping Yang #、Ronghua Wang *、Wang Fang #*",
      "address": "该作者对应的所有机构地址英文原文，多个机构用中文分号；分隔，不换行",
      "email": "该作者邮箱，非通讯作者通常无此信息，留空",
      "phone": "该作者电话，非通讯作者通常无此信息，留空"
    }
  ],
  "all_authors_info_cn": [
    {
      "name": "作者姓名，保留英文拼音原样，并在姓名后附上该作者原本的符号标记，如 Weiping Yang #、Ronghua Wang *、Wang Fang #*",
      "address": "该作者对应的所有机构地址中文翻译，多个机构用中文分号；分隔，不换行",
      "email": "该作者邮箱，非通讯作者通常无此信息，留空",
      "phone": "该作者电话，非通讯作者通常无此信息，留空"
    }
  ]
}
```

注意：all_authors_info 和 all_authors_info_cn 按论文中作者的原始顺序排列，包含论文所有作者，不限国籍。字段缺失时留空字符串。


# 示例

输入作者列表：
Weiping Yang 1,#, Wei Xiao 2,#, Wenhao Xu 3,#, Lijun Ren 1, Tao Li 3,4,*, Wei Zhao 1,3,*

机构列表：
1. School of Basic Medical Sciences, Ningxia Medical University, Yinchuan, China
2. Department of Pediatrics, General Hospital of Ningxia Medical University, Yinchuan, China
3. Ningxia Key Laboratory for Prevention of Common Infectious Diseases, Yinchuan, China
4. Department of Hepatobiliary Surgery, General Hospital of Ningxia Medical University, Yinchuan, China

脚注：
## These authors contributed equally to this work
* Corresponding author: taoli@email.com

输出：

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


# 论文内容
