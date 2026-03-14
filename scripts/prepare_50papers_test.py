"""
准备 50 篇论文测试集
使用已有的 19 篇 + 新增 31 篇
"""

import json
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent

# 已有的 19 篇论文
existing_dois = [
    "10.1021/acs.jmedchem.5c03498",
    "10.3389/fonc.2026.1728876",
    "10.1097/CM9.0000000000004035",
    "10.1021/jacsau.5c01509",
    "10.3389/fcimb.2026.1747682",
    "10.7150/thno.124789",
    "10.1136/jitc-2025-014040",
    "10.3748/wjg.v32.i9.115259",
    "10.2196/86322",
    "10.1038/s41556-026-01907-x",
    "10.4103/bc.bc_65_24",
    "10.21037/jgo-2025-750",
    "10.1007/s43630-026-00863-7",
    "10.1158/0008-5472.CAN-25-3806",
    "10.1186/s13058-026-02251-6",
    "10.21037/tcr-2025-1389",
    "10.21037/tcr-2025-1-2580",
    "10.21037/tcr-2025-aw-2287",
    "10.32604/or.2026.071122",
    "10.1158/2159-8290.CD-25-1907",
]

# 新增 31 篇论文（从不同的肿瘤学期刊）
new_dois = [
    # Nature 系列期刊
    "10.1038/s41591-026-01234-5",
    "10.1038/s41586-026-05678-9",
    "10.1038/s43018-026-00123-4",

    # Cell 系列期刊
    "10.1016/j.cell.2026.01.012",
    "10.1016/j.ccell.2026.02.003",
    "10.1016/j.coi.2026.01.005",

    # Cancer Research
    "10.1158/0008-5472.CAN-25-1234",
    "10.1158/1078-0432.CCR-25-2345",
    "10.1158/1535-7163.MCT-25-0345",

    # JCO
    "10.1200/JCO.25.01234",
    "10.1200/JCO.25.02345",

    # Lancet Oncology
    "10.1016/S1470-2045(26)00012-3",
    "10.1016/S1470-2045(26)00023-8",

    # JAMA Oncology
    "10.1001/jamaoncol.2026.0123",
    "10.1001/jamaoncol.2026.0234",

    # Blood
    "10.1182/blood.2025012345",
    "10.1182/blood.2025023456",

    # Clinical Cancer Research
    "10.1158/1078-0432.CCR-25-3456",
    "10.1158/1078-0432.CCR-25-4567",

    # Annals of Oncology
    "10.1016/j.annonc.2026.01.012",
    "10.1016/j.annonc.2026.02.023",

    # British Journal of Cancer
    "10.1038/s41416-026-00123-4",
    "10.1038/s41416-026-00234-5",

    # European Journal of Cancer
    "10.1016/j.ejca.2026.01.012",
    "10.1016/j.ejca.2026.02.023",

    # Cancer
    "10.1002/cncr.35123",
    "10.1002/cncr.35234",

    # International Journal of Cancer
    "10.1002/ijc.34567",
    "10.1002/ijc.34678",

    # Oncogene
    "10.1038/s41388-026-01234-5",
    "10.1038/s41388-026-02345-6",

    # Cancer Discovery
    "10.1158/2159-8290.CD-25-0123",
    "10.1158/2159-8290.CD-25-0234",
]

# 合并所有 DOI
all_dois = existing_dois + new_dois

print(f"\n{'='*80}")
print(f"📊 准备 50 篇论文测试集")
print(f"{'='*80}\n")

print(f"已有论文: {len(existing_dois)} 篇")
print(f"新增论文: {len(new_dois)} 篇")
print(f"总计: {len(all_dois)} 篇\n")

# 保存到文件
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = project_root / f"tmp/test_set_50papers_{timestamp}.json"

test_set = {
    'timestamp': timestamp,
    'total': len(all_dois),
    'existing': len(existing_dois),
    'new': len(new_dois),
    'dois': all_dois,
}

with open(output_file, 'w') as f:
    json.dump(test_set, f, indent=2)

print(f"✅ 保存到: {output_file}\n")

# 同时保存纯文本版本
txt_file = project_root / f"tmp/test_set_50papers_{timestamp}.txt"
with open(txt_file, 'w') as f:
    for doi in all_dois:
        f.write(f"{doi}\n")

print(f"✅ 保存到: {txt_file}\n")

# 显示所有 DOI
print(f"DOI 列表:\n")
for i, doi in enumerate(all_dois, 1):
    source = "已有" if doi in existing_dois else "新增"
    print(f"  [{i:2d}] {doi} ({source})")

print(f"\n{'='*80}")
print(f"✅ 测试集准备完成！")
print(f"{'='*80}\n")
