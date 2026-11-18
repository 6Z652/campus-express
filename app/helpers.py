"""sqlite3.Row -> 响应字典 的统一序列化。"""
from __future__ import annotations

from typing import Dict


def package_to_dict(row) -> Dict:
    return {
        "id": row["id"],
        "tracking_no": row["tracking_no"],
        "student_id": row["student_id"],
        "student_name": row["student_name"],
        "phone": row["phone"],
        "size": row["size"],
        "shelf": {
            "area": row["area"],
            "level": row["level"],
            "slot": row["slot"],
            "label": row["shelf_label"],
        },
        "pickup_code": row["pickup_code"],
        "status": row["status"],
        "created_at": row["created_at"],
        "picked_up_at": row["picked_up_at"],
    }
