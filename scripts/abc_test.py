"""
A/B/C 测试脚本
V1: 不截断 + 长 Prompt
V2: 截断 + 精简 Prompt
V3: 截断 + 长 Prompt

测试 20 篇论文，对比：
1. Token 消耗
2. 提取准确性
3. 处理速度
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Callable

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.crawlers.jina_client import JinaClient
from src.processors.content_truncator import ContentTruncator
from src.logging_config import get_logger


# 测试集（20 篇论文）
TEST_DOIS = [
    "10.1021/acs.jmedchem.5c03498",  # J. Med. Chem.
    "10.3389/fonc.2026.1728876",  # Frontiers in Oncology
    "10.1097/CM9.0000000000004035",  # Chinese Medical Journal
    "10.1021/jacsau.5c01509",  # JACS Au
    "10.3389/fcimb.2026.1747682",  # Frontiers in Cellular and Infection Microbiology
    "10.7150/thno.124789",  # Theranostics
]
    "10.1136/jitc-2025-014040",  # Journal for ImmunoTherapy of Cancer
    "10.3748/wjg.v32.i9.115259",  # World Journal of Gastroenterology
    "10.2196/86322",  # JMIR
    "10.1038/s41556-026-01907-x",  # Nature Cell Biology
    "10.4103/bc.bc_65_24",  # Blood Cancer
    "10.21037/jgo-2025-750",  # Journal of Gastrointestinal Oncology
    "10.1007/s43630-026-00863-7",  # Biochimica et Biophysica Acta
    "10.1158/0008-5472.CAN-25-3806",  # Cancer Research
    "10.1186/s13058-026-02251-6",  # Breast Cancer Research
    "10.21037/tcr-2025-1389",  # Translational Cancer Research
    "10.21037/tcr-2025-1-2580",  # Translational Cancer Research
    "10.21037/tcr-2025-aw-2287",  # Translational Cancer Research
    "10.32604/or.2026.071122",  # Oncology Reports
    "10.1158/2159-8290.CD-25-1907",  # Cancer Discovery
]

