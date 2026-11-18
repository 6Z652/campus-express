"""UC-01~UC-04 的 API 集成测试：正常流 + 异常分支。

所有请求通过 FastAPI TestClient 完成，不启动任何常驻后台服务。
"""
from __future__ import annotations

import re

from app.codes import CODE_RE
from app.db import get_connection

CODE = "A-1-01-001"          # seed 中张三的第 1 个包裹
NEW_TRACKING = "SF9990000001"


# ---------------------------------------------------------------- 健康检查

def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ---------------------------------------------------------------- UC-01 正常流

def test_uc01_lookup_get_aggregates_same_student(client):
    """取件码 -> 解析货架号 -> 聚合返回同一学生的多个包裹。"""
    r = client.get("/api/packages/lookup", params={"code": CODE})
    assert r.status_code == 200
    d = r.json()
    assert d["code"] == CODE
    assert d["shelf"]["area"] == "A" and d["shelf"]["level"] == 1 and d["shelf"]["slot"] == 1
    assert d["shelf"]["shelf"] == "A区-1层-01格"
    assert d["student"]["name"] == "张三"
    assert d["student"]["id"] == "S2021001"
    assert d["total"] == 3                       # 张三在 seed 中有 3 个包裹
    assert len(d["packages"]) == 3
    assert {p["pickup_code"] for p in d["packages"]} == {
        "A-1-01-001", "A-1-02-002", "A-1-03-003"
    }


def test_uc01_lookup_post_also_supported(client):
    """需求要求 POST/GET 均可用。"""
    r = client.post("/api/packages/lookup", params={"code": CODE})
    assert r.status_code == 200
    assert r.json()["total"] == 3


# ---------------------------------------------------------------- UC-02 正常流

def test_uc02_forecast(client):
    r = client.get("/api/queue/forecast")
    assert r.status_code == 200
    d = r.json()
    for key in (
        "current_hour", "pending_count", "servers", "avg_service_minutes",
        "predicted_wait_minutes", "congestion_level", "recommended_offpeak_hour",
        "recommendation", "algorithm",
    ):
        assert key in d
    assert d["pending_count"] == 5            # seed 有 5 个在库包裹
    assert d["predicted_wait_minutes"] >= 0
    assert 0 <= d["recommended_offpeak_hour"] <= 23
    assert "wait = ceil" in d["algorithm"]


# ---------------------------------------------------------------- UC-03 正常流

def test_uc03_checkin_assigns_shelf_and_code(client):
    r = client.post("/api/packages/checkin", json={
        "tracking_no": NEW_TRACKING,
        "student_id": "S2021004",
        "student_name": "赵六",
        "phone": "13800004004",
        "size": "large",
    })
    assert r.status_code == 200
    d = r.json()
    assert d["created"] is True and d["idempotent"] is False
    assert d["pickup_code"] == "A-1-06-006"     # 序号 6 -> A区-1层-06格
    assert re.match(CODE_RE, d["pickup_code"])
    assert d["shelf"]["label"] == "A区-1层-06格"
    assert d["package"]["status"] == "in_stock"

    # 入库结果可立即被 UC-01 查询到
    q = client.get("/api/packages/lookup", params={"code": d["pickup_code"]})
    assert q.status_code == 200
    assert q.json()["packages"][0]["tracking_no"] == NEW_TRACKING


def test_uc03_checkin_idempotent(client):
    """重复运单号不重复入库。"""
    payload = {
        "tracking_no": NEW_TRACKING, "student_id": "S2021004",
        "student_name": "赵六", "phone": "13800004004",
    }
    r1 = client.post("/api/packages/checkin", json=payload)
    r2 = client.post("/api/packages/checkin", json=payload)
    assert r1.json()["created"] is True
    assert r2.status_code == 200
    assert r2.json()["created"] is False and r2.json()["idempotent"] is True
    assert r2.json()["pickup_code"] == r1.json()["pickup_code"]

    conn = get_connection()
    n = conn.execute(
        "SELECT COUNT(*) AS n FROM packages WHERE tracking_no=?", (NEW_TRACKING,)
    ).fetchone()["n"]
    conn.close()
    assert n == 1


# ---------------------------------------------------------------- UC-04 正常流

def test_uc04_authorize_and_query(client):
    r = client.post("/api/packages/authorize", json={
        "pickup_code": CODE, "delegate_name": "同学甲",
        "delegate_phone": "13800000000", "ttl_minutes": 30,
    })
    assert r.status_code == 200
    auth = r.json()["auth_code"]
    assert len(auth) == 6 and auth.isdigit()

    q = client.get(f"/api/packages/authorize/{CODE}")
    assert q.status_code == 200
    d = q.json()
    assert d["valid"] is True
    assert d["active_authorization"]["auth_code"] == auth
    assert d["active_authorization"]["expired"] is False


def test_uc04_checkout_self(client):
    r = client.post("/api/packages/checkout", json={
        "pickup_code": CODE, "operator": "值班员A",
    })
    assert r.status_code == 200
    d = r.json()
    assert d["checked_out"] is True
    assert d["auth_code_used"] is None
    assert d["package"]["status"] == "picked_up"


def test_uc04_checkout_with_delegate_auth(client):
    auth = client.post("/api/packages/authorize", json={
        "pickup_code": CODE, "delegate_name": "同学甲", "ttl_minutes": 30,
    }).json()["auth_code"]
    r = client.post("/api/packages/checkout", json={
        "pickup_code": CODE, "auth_code": auth, "operator": "值班员A",
    })
    assert r.status_code == 200
    assert r.json()["auth_code_used"] == auth
    assert r.json()["package"]["status"] == "picked_up"


def test_uc04_exception_registration(client):
    r = client.post("/api/packages/checkout", json={
        "pickup_code": CODE, "operator": "值班员A",
        "note": "外包装破损", "report_exception": True,
    })
    assert r.status_code == 200
    d = r.json()
    assert d["exception_registered"] is True and d["checked_out"] is False
    assert d["reason"] == "外包装破损"
    assert d["package"]["status"] == "exception"

    q = client.get("/api/packages/exceptions")
    assert q.status_code == 200
    assert q.json()["total"] == 1
    assert q.json()["exceptions"][0]["pickup_code"] == CODE


# ---------------------------------------------------------------- 异常分支（>=6）

def test_uc01_invalid_code_format(client):
    r = client.get("/api/packages/lookup", params={"code": "not-a-code"})
    assert r.status_code == 400
    assert "格式非法" in r.json()["detail"]


def test_uc01_code_not_found(client):
    """格式合法但不存在的取件码。"""
    r = client.get("/api/packages/lookup", params={"code": "F-5-20-999"})
    assert r.status_code == 404
    assert "不存在" in r.json()["detail"]


def test_uc01_missing_code_param(client):
    r = client.get("/api/packages/lookup")
    assert r.status_code == 422


def test_uc03_missing_required_field(client):
    r = client.post("/api/packages/checkin", json={"student_id": "S1"})
    assert r.status_code == 422


def test_uc04_authorize_nonexistent_code(client):
    r = client.post("/api/packages/authorize", json={
        "pickup_code": "F-5-20-999", "delegate_name": "同学甲",
    })
    assert r.status_code == 404


def test_uc04_authorize_duplicate(client):
    client.post("/api/packages/authorize", json={
        "pickup_code": CODE, "delegate_name": "同学甲", "ttl_minutes": 30,
    })
    r = client.post("/api/packages/authorize", json={
        "pickup_code": CODE, "delegate_name": "同学乙", "ttl_minutes": 30,
    })
    assert r.status_code == 409
    assert "已有有效授权" in r.json()["detail"]


def test_uc04_authorize_on_picked_up_package(client):
    client.post("/api/packages/checkout", json={"pickup_code": CODE})
    r = client.post("/api/packages/authorize", json={
        "pickup_code": CODE, "delegate_name": "同学甲",
    })
    assert r.status_code == 409
    assert "不在库" in r.json()["detail"]


def test_uc04_checkout_nonexistent_code(client):
    r = client.post("/api/packages/checkout", json={"pickup_code": "F-5-20-999"})
    assert r.status_code == 404


def test_uc04_checkout_duplicate(client):
    client.post("/api/packages/checkout", json={"pickup_code": CODE})
    r = client.post("/api/packages/checkout", json={"pickup_code": CODE})
    assert r.status_code == 409
    assert "重复出库" in r.json()["detail"]


def test_uc04_checkout_wrong_auth_code(client):
    r = client.post("/api/packages/checkout", json={
        "pickup_code": CODE, "auth_code": "000000",
    })
    assert r.status_code == 403
    assert "无效" in r.json()["detail"]


def test_uc04_checkout_expired_auth(client):
    """ttl_minutes=0 构造立即过期授权。"""
    auth = client.post("/api/packages/authorize", json={
        "pickup_code": CODE, "delegate_name": "同学甲", "ttl_minutes": 0,
    }).json()["auth_code"]
    q = client.get(f"/api/packages/authorize/{CODE}")
    assert q.json()["valid"] is False
    assert q.json()["authorizations"][0]["expired"] is True

    r = client.post("/api/packages/checkout", json={
        "pickup_code": CODE, "auth_code": auth,
    })
    assert r.status_code == 403
    assert "过期" in r.json()["detail"]


def test_uc04_checkout_reused_auth_code(client):
    auth = client.post("/api/packages/authorize", json={
        "pickup_code": CODE, "delegate_name": "同学甲", "ttl_minutes": 30,
    }).json()["auth_code"]
    client.post("/api/packages/checkout", json={
        "pickup_code": CODE, "auth_code": auth,
    })
    # 模拟包裹重新上架，以验证授权码「已使用」分支
    conn = get_connection()
    conn.execute(
        "UPDATE packages SET status='in_stock', picked_up_at=NULL WHERE pickup_code=?",
        (CODE,),
    )
    conn.commit()
    conn.close()

    r = client.post("/api/packages/checkout", json={
        "pickup_code": CODE, "auth_code": auth,
    })
    assert r.status_code == 409
    assert "已使用" in r.json()["detail"]


def test_uc04_query_auth_nonexistent_code(client):
    r = client.get("/api/packages/authorize/F-5-20-999")
    assert r.status_code == 404


def test_uc04_query_auth_never_authorized(client):
    r = client.get(f"/api/packages/authorize/{CODE}")
    assert r.status_code == 200
    assert r.json()["valid"] is False
    assert r.json()["reason"] == "从未授权"
