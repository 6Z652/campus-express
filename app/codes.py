"""取件码的生成与解析（UC-01 / UC-03 共用）。

格式：  <区>-<层>-<格>-<序号>        示例： A-3-02-007
正则：  ^([A-F])-([1-5])-(\\d{2})-(\\d{3,6})$

- 区   A~F 共 6 个货架区
- 层   1~5 层
- 格   01~20 格（两位补零）
- 序号 取件记录自增主键，补足 3 位；超过 999 时自然扩展为 4~6 位

取件码本身即"编码了货架号"，解析后可还原货架位；查库时以完整取件码为键。
"""
from __future__ import annotations

import re
from typing import Dict, Optional

CODE_RE = re.compile(r"^([A-F])-([1-5])-(\d{2})-(\d{3,6})$")

SHELF_AREAS = "ABCDEF"
LEVELS_PER_AREA = 5
SLOTS_PER_LEVEL = 20


def shelf_position(index: int) -> Dict:
    """按入库序号（从 1 开始）确定性分配货架位。

    index=1 -> A区-1层-01格；每 20 个换一层，每 100 个换一区（循环）。
    """
    i = index - 1
    area = SHELF_AREAS[(i // (LEVELS_PER_AREA * SLOTS_PER_LEVEL)) % len(SHELF_AREAS)]
    level = (i // SLOTS_PER_LEVEL) % LEVELS_PER_AREA + 1
    slot = i % SLOTS_PER_LEVEL + 1
    return {
        "area": area,
        "level": level,
        "slot": slot,
        "label": f"{area}区-{level}层-{slot:02d}格",
    }


def make_pickup_code(index: int, position: Dict) -> str:
    """由货架位 + 入库序号生成取件码（序号取主键，保证唯一）。"""
    return f"{position['area']}-{position['level']}-{position['slot']:02d}-{index:03d}"


def parse_pickup_code(code: str) -> Optional[Dict]:
    """解析取件码并还原货架号；格式非法返回 None。"""
    if not isinstance(code, str):
        return None
    cleaned = code.strip()
    m = CODE_RE.match(cleaned)
    if not m:
        return None
    area, level, slot, seq = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
    return {
        "code": cleaned,
        "area": area,
        "level": level,
        "slot": slot,
        "sequence": seq,
        "shelf": f"{area}区-{level}层-{slot:02d}格",
    }
