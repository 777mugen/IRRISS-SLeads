"""
浏览器验证：打开关键论文核对通讯作者信息
"""

# 需要验证的论文（V1 vs V2/V3 有差异）

验证列表 = [
    {
        "DOI": "10.1007/s43630-026-00863-7",
        "URL": "https://doi.org/10.1007/s43630-026-00863-7",
        "V1_通讯作者": "Linglin Zhang",
        "V1_邮箱": "1700207@tongji.edu.cn",
        "V2/V3_通讯作者": "Ronald Sroka",
        "V2/V3_邮箱": "None",
    },
    {
        "DOI": "10.1136/jitc-2025-014040",
        "URL": "https://doi.org/10.1136/jitc-2025-014040",
        "V1_通讯作者": "Jumei Shi",
        "V1_邮箱": "shijumei@tongji.edu.cn",
        "V2/V3_通讯作者": "Zhuning Wang",
        "V2/V3_邮箱": "None",
    },
    {
        "DOI": "10.1038/s41556-026-01907-x",
        "URL": "https://doi.org/10.1038/s41556-026-01907-x",
        "V1_通讯作者": "Tian Tian",
        "V1_邮箱": "tiantian99@jnu.edu.cn",
        "V2/V3_通讯作者": "Huai-Qiang Ju",
        "V2/V3_邮箱": "None",
    },
]

for paper in 验证列表:
    print(f"\n{'='*80}")
    print(f"论文: {paper['DOI']}")
    print(f"{'='*80}")
    print(f"\nV1 提取:")
    print(f"  通讯作者: {paper['V1_通讯作者']}")
    print(f"  邮箱: {paper['V1_邮箱']}")
    print(f"\nV2/V3 提取:")
    print(f"  通讯作者: {paper['V2/V3_通讯作者']}")
    print(f"  邮箱: {paper['V2/V3_邮箱']}")
    print(f"\n浏览器验证:")
    print(f"  👉 请打开: {paper['URL']}")
    print(f"  👉 查看论文末尾的通讯作者标注")
    print(f"  👉 核对邮箱地址")
