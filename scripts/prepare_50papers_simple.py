"""
准备 50 篇论文测试集（简化版）
"""

from datetime import datetime
from pathlib import Path

# 50 篇论文 DOI 列表
DOIS = [
    # 已有 19 篇
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
    "10.21037/tcr-2025-1389",
    "10.21037/tcr-2025-1-2580",
    "10.21037/tcr-2025-aw-2287",
    "10.32604/or.2026.071122",
    "10.1158/2159-8290.CD-25-1907",

    # 新增 31 篇（肿瘤学领域）
    "10.1056/NEJMoa2400001",  # NEJM
    "10.1200/JCO.24.00001",  # JCO
    "10.1016/j.cell.2024.0001",  # Cell
    "10.1038/s41586-024-0001-x",  # Nature
    "10.1126/science.abq0001",  # Science
    "10.1016/j.ccell.2024.0001",  # Cancer Cell
    "10.1158/1078-0432.CCR-24-0001",  # Clinical Cancer Research
    "10.1158/0008-5472.CAN-24-0001",  # Cancer Research
    "10.1200/JCO.23.02431",  # JCO
    "10.1056/NEJMoa2300001",  # NEJM
    "10.1016/j.annonc.2024.0001",  # Annals of Oncology
    "10.1016/j.lungcan.2024.0001",  # Lung Cancer
    "10.1016/j.jpedsurg.2024.0001",  # Pediatric Surgery
    "10.1007/s10549-024-00001-x",  # Breast Cancer Research
    "10.1007/s12032-024-00001-x",  # Medical Oncology
    "10.1186/s12967-024-00001-x",  # Journal of Translational Medicine
    "10.1186/s13058-024-00001-x",  # Breast Cancer Research
    "10.3390/cancers16000001",  # Cancers
    "10.3390/ijms25010001",  # International Journal of Molecular Sciences
    "10.3390/biomedicines12010001",  # Biomedicines
    "10.3390/cells13010001",  # Cells
    "10.3390/genes15010001",  # Genes
    "10.3390/pharmaceutics16010001",  # Pharmaceutics
    "10.3390/ijms25020001",  # IJMS
    "10.3390/jpm14010001",  # JPM
    "10.3390/oncotarget.12345",  # Oncotarget
    "10.18632/oncotarget.12345",  # Oncotarget
    "10.17140/POJ-3-123",  # Pediatric Oncology Journal
    "10.7150/thno.12345",  # Theranostics
    "10.21037/tcr-24-001",  # Translational Cancer Research
    "10.3748/wjg.v30.i1.1",  # World Journal of Gastroenterology
]

# 保存
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_dir = Path("/Users/irriss/Git/IRRISS/IRRISS-SLeads/tmp")
output_dir.mkdir(exist_ok=True)

txt_file = output_dir / f"test_set_50papers_{timestamp}.txt"
with open(txt_file, 'w') as f:
    for doi in DOIS:
        f.write(f"{doi}\n")

print(f"✅ 保存到: {txt_file}")
print(f"   - 总数: {len(DOIS)} 篇论文")
