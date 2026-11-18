"""UC-01 取件码解析与包裹聚合查询。

GET/POST /api/packages/lookup?code=A-1-01-001
  1) 校验取件码格式 -> 非法 400
  2) 解析出货架号（区-层-格）
  3) 按取件码定位包裹 -> 不存在 404
  4) 以 student_id 聚合返回该学生的全部包裹
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..codes import parse_pickup_code
from ..db import get_connection
from ..helpers import package_to_dict

router = APIRouter(prefix="/api/packages", tags=["UC-01 取件码解析与包裹聚合查询"])


@router.api_route("/lookup", methods=["GET", "POST"])
def lookup(code: str = Query(..., description="取件码，例如 A-1-01-001")):
    parsed = parse_pickup_code(code)
    if parsed is None:
        raise HTTPException(
            status_code=400,
            detail=f"取件码格式非法: {code!r}，正确格式如 A-1-01-001",
        )

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM packages WHERE pickup_code=?", (parsed["code"],)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"取件码不存在: {parsed['code']}")
        rows = conn.execute(
            "SELECT * FROM packages WHERE student_id=? ORDER BY id", (row["student_id"],)
        ).fetchall()
    finally:
        conn.close()

    return {
        "code": parsed["code"],
        "shelf": parsed,
        "student": {
            "id": row["student_id"],
            "name": row["student_name"],
            "phone": row["phone"],
        },
        "total": len(rows),
        "packages": [package_to_dict(r) for r in rows],
    }
