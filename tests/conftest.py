"""pytest 配置：把项目根加入 sys.path，使测试可以用 ``import src``。"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
