"""UC-04 出库核验与代取授权。

POST /api/packages/authorize            生成代取授权码
GET  /api/packages/authorize/{code}     查询某取件码的授权状态（含过期判定）
POST /api/packages/checkout             出库核验（本人 / 代取 / 异常件登记）
GET  /api/packages/exceptions           已登记异常件清单

异常分支：取件码不存在 404、重复出库 409、授权码错误 403、
          授权过期 403、授权码重复使用 409、对非在库包裹授权 409、
          重复授权 409、对非在库包裹登记异常件 409、
          重复登记异常件 409。
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException

from ..db import get_connection
from ..helpers import package_to_dict
from ..schemas import AuthorizeRequest, CheckoutRequest

router = APIRouter(prefix="/api/packages", tags=["UC-04 出库核验与代取授权"])


def _auth_status(row, now: datetime) -> dict:
    """把一条 authorization 记录解析为含有效期的状态字典。"""
    used = bool(row["used"])
    expired = now >= datetime.fromisoformat(row["expires_at"])
    valid = (not used) and (not expired)
    reason = "有效" if valid else ("授权码已使用" if used else "授权已过期")
    return {
        "auth_code": row["auth_code"],
        "delegate_name": row["delegate_name"],
        "delegate_phone": row["delegate_phone"],
        "expires_at": row["expires_at"],
        "used": used,
        "expired": expired,
        "valid": valid,
        "reason": reason,
        "created_at": row["created_at"],
    }


@router.post("/authorize")
def authorize(req: AuthorizeRequest):
    conn = get_connection()
    try:
        pkg = conn.execute(
            "SELECT * FROM packages WHERE pickup_code=?", (req.pickup_code,)
        ).fetchone()
        if pkg is None:
            raise HTTPException(status_code=404, detail=f"取件码不存在: {req.pickup_code}")
        if pkg["status"] != "in_stock":
            raise HTTPException(
                status_code=409,
                detail=f"包裹不在库，无法授权，当前状态: {pkg['status']}",
            )

        now = datetime.now()
        rows = conn.execute(
            "SELECT * FROM authorizations WHERE pickup_code=? ORDER BY id DESC",
            (req.pickup_code,),
        ).fetchall()
        for r in rows:
            if _auth_status(r, now)["valid"]:
                raise HTTPException(status_code=409, detail="该取件码已有有效授权，请勿重复授权")

        auth_code = f"{secrets.randbelow(1000000):06d}"
        while conn.execute(
            "SELECT 1 FROM authorizations WHERE auth_code=?", (auth_code,)
        ).fetchone():
            auth_code = f"{secrets.randbelow(1000000):06d}"

        expires_at = (now + timedelta(minutes=req.ttl_minutes)).isoformat(timespec="seconds")
        conn.execute(
            "INSERT INTO authorizations "
            "(pickup_code, delegate_name, delegate_phone, auth_code, expires_at, used, created_at) "
            "VALUES (?,?,?,?,?,0,?)",
            (
                req.pickup_code, req.delegate_name, req.delegate_phone,
                auth_code, expires_at, now.isoformat(timespec="seconds"),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "created": True,
        "pickup_code": req.pickup_code,
        "auth_code": auth_code,
        "delegate_name": req.delegate_name,
        "expires_at": expires_at,
        "ttl_minutes": req.ttl_minutes,
        "message": "代取授权已生成",
    }


@router.get("/authorize/{code}")
def get_authorization(code: str):
    """{code} 为取件码：返回该包裹的全部授权及其有效/过期状态。"""
    conn = get_connection()
    try:
        pkg = conn.execute(
            "SELECT * FROM packages WHERE pickup_code=?", (code,)
        ).fetchone()
        if pkg is None:
            raise HTTPException(status_code=404, detail=f"取件码不存在: {code}")
        rows = conn.execute(
            "SELECT * FROM authorizations WHERE pickup_code=? ORDER BY id DESC", (code,)
        ).fetchall()
    finally:
        conn.close()

    now = datetime.now()
    statuses = [_auth_status(r, now) for r in rows]
    active = next((s for s in statuses if s["valid"]), None)
    return {
        "pickup_code": code,
        "has_authorization": bool(statuses),
        "active_authorization": active,
        "valid": active is not None,
        "reason": (
            "有效授权存在" if active
            else ("从未授权" if not statuses else "无有效授权（已过期或已使用）")
        ),
        "authorizations": statuses,
    }


@router.post("/checkout")
def checkout(req: CheckoutRequest):
    conn = get_connection()
    try:
        pkg = conn.execute(
            "SELECT * FROM packages WHERE pickup_code=?", (req.pickup_code,)
        ).fetchone()
        if pkg is None:
            raise HTTPException(status_code=404, detail=f"取件码不存在: {req.pickup_code}")

        now = datetime.now()
        now_s = now.isoformat(timespec="seconds")

        # 异常件登记：只登记不出库，包裹状态置为 exception
        # 前置校验：只有仍在库的包裹才允许登记异常件。
        # 否则会出现两种状态机回退：已出库包裹被改回 exception、异常件被重复登记。
        if req.report_exception:
            if pkg["status"] == "exception":
                raise HTTPException(
                    status_code=409,
                    detail=f"该包裹已登记为异常件，请勿重复登记: {req.pickup_code}",
                )
            if pkg["status"] != "in_stock":
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"包裹已出库，不可再登记异常件，当前状态: {pkg['status']}"
                        f"，出库时间: {pkg['picked_up_at']}"
                    ),
                )

            reason = req.note or "包裹异常（破损/信息不符），暂停出库"
            conn.execute(
                "INSERT INTO exceptions (pickup_code, tracking_no, reason, operator, created_at) "
                "VALUES (?,?,?,?,?)",
                (req.pickup_code, pkg["tracking_no"], reason, req.operator, now_s),
            )
            conn.execute("UPDATE packages SET status='exception' WHERE id=?", (pkg["id"],))
            conn.commit()
            row = conn.execute("SELECT * FROM packages WHERE id=?", (pkg["id"],)).fetchone()
            return {
                "checked_out": False,
                "exception_registered": True,
                "reason": reason,
                "message": "异常件已登记，包裹暂停出库",
                "package": package_to_dict(row),
            }

        if pkg["status"] != "in_stock":
            raise HTTPException(
                status_code=409,
                detail=f"重复出库或包裹不可出库，当前状态: {pkg['status']}",
            )

        used_auth = None
        if req.auth_code:
            auth = conn.execute(
                "SELECT * FROM authorizations WHERE auth_code=?", (req.auth_code,)
            ).fetchone()
            if auth is None or auth["pickup_code"] != req.pickup_code:
                raise HTTPException(status_code=403, detail="代取授权码无效或与取件码不匹配")
            st = _auth_status(auth, now)
            if st["used"]:
                raise HTTPException(status_code=409, detail="代取授权码已使用")
            if st["expired"]:
                raise HTTPException(status_code=403, detail="代取授权已过期，请重新授权")
            used_auth = auth["auth_code"]

        conn.execute(
            "UPDATE packages SET status='picked_up', picked_up_at=? WHERE id=?",
            (now_s, pkg["id"]),
        )
        if used_auth:
            conn.execute("UPDATE authorizations SET used=1 WHERE auth_code=?", (used_auth,))
        conn.commit()
        row = conn.execute("SELECT * FROM packages WHERE id=?", (pkg["id"],)).fetchone()
    finally:
        conn.close()

    return {
        "checked_out": True,
        "exception_registered": False,
        "pickup_code": req.pickup_code,
        "auth_code_used": used_auth,
        "operator": req.operator,
        "picked_up_at": now_s,
        "message": "代取出库核验通过" if used_auth else "本人取件出库核验通过",
        "package": package_to_dict(row),
    }


@router.get("/exceptions")
def list_exceptions():
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM exceptions ORDER BY id").fetchall()
    finally:
        conn.close()
    return {"total": len(rows), "exceptions": [dict(r) for r in rows]}
