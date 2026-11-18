"""UC-03 入库与货架分配。

POST /api/packages/checkin
  扫码入库 -> 自动分配货架位（区-层-格）-> 生成取件码。
  幂等：同一 tracking_no 重复提交不重复入库，返回已存在记录。
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

from ..codes import make_pickup_code, shelf_position
from ..db import get_connection
from ..helpers import package_to_dict
from ..schemas import CheckinRequest

router = APIRouter(prefix="/api/packages", tags=["UC-03 入库与货架分配"])


@router.post("/checkin")
def checkin(req: CheckinRequest):
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT * FROM packages WHERE tracking_no=?", (req.tracking_no,)
        ).fetchone()
        if existing is not None:
            return {
                "created": False,
                "idempotent": True,
                "message": "运单号已存在，跳过重复入库",
                "pickup_code": existing["pickup_code"],
                "shelf": {
                    "area": existing["area"],
                    "level": existing["level"],
                    "slot": existing["slot"],
                    "label": existing["shelf_label"],
                },
                "package": package_to_dict(existing),
            }

        # 用 MAX(id)+1 作为入库序号，保证取件码序号与实际主键一致且唯一
        index = conn.execute(
            "SELECT COALESCE(MAX(id),0)+1 AS n FROM packages"
        ).fetchone()["n"]
        pos = shelf_position(index)
        code = make_pickup_code(index, pos)
        now = datetime.now().isoformat(timespec="seconds")

        cur = conn.execute(
            "INSERT INTO packages "
            "(tracking_no, student_id, student_name, phone, size, area, level, slot, "
            " shelf_label, pickup_code, status, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,'in_stock',?)",
            (
                req.tracking_no, req.student_id, req.student_name, req.phone, req.size,
                pos["area"], pos["level"], pos["slot"], pos["label"], code, now,
            ),
        )
        row = conn.execute("SELECT * FROM packages WHERE id=?", (cur.lastrowid,)).fetchone()
        conn.commit()
    finally:
        conn.close()

    return {
        "created": True,
        "idempotent": False,
        "message": "入库成功",
        "pickup_code": code,
        "shelf": pos,
        "package": package_to_dict(row),
    }
