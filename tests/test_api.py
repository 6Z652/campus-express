"""UC-01~UC-04 的 API 集成测试：正常流 + 异常分支。

所有请求通过 FastAPI TestClient 完成，不启动任何常驻后台服务。
"""
from __future__ import annotations

import re

from app.codes import CODE_RE
from app.db import get_connection

CODE = "A-1-01-001"          # seed 中张三的第 1 个包裹
OTHER = "A-1-02-002"         # seed 中张三的第 2 个包裹（用于构造「授权码/取件码不匹配」）
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


# ------------------------------------------------- UC-01 补充边界（本次迭代新增）

def test_uc01_lookup_trims_surrounding_space(client):
    """取件码首尾含空格时应先裁剪再解析，仍按正常流返回。"""
    r = client.get("/api/packages/lookup", params={"code": "  A-1-01-001  "})
    assert r.status_code == 200
    d = r.json()
    assert d["code"] == "A-1-01-001"          # 回显的是裁剪后的取件码
    assert d["total"] == 3


def test_uc01_lowercase_area_is_rejected(client):
    """区号只允许大写 A~F；小写与入库生成规则不一致，应判格式非法。"""
    r = client.get("/api/packages/lookup", params={"code": "a-1-01-001"})
    assert r.status_code == 400
    assert "格式非法" in r.json()["detail"]


def test_uc01_newly_checked_in_package_is_queryable(client):
    """入库生成的取件码可立即被 UC-01 查到，且解析货架号与入库存储一致。"""
    inp = {"tracking_no": "SF9990000009", "student_id": "S2021009",
           "student_name": "孙九", "phone": "13800004009"}
    r = client.post("/api/packages/checkin", json=inp)
    assert r.status_code == 200
    code = r.json()["pickup_code"]            # 第 6 件 -> A-1-06-006

    q = client.get("/api/packages/lookup", params={"code": code})
    assert q.status_code == 200
    d = q.json()
    assert d["code"] == code
    assert d["student"]["name"] == "孙九"
    assert d["total"] == 1
    assert d["packages"][0]["tracking_no"] == "SF9990000009"
    assert d["packages"][0]["shelf"]["label"] == d["shelf"]["shelf"]


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


# ------------------------------------------------------------------
def test_uc03_idempotent_keeps_first_record(client):
    """E4：同运单号重复提交，以首次入库信息为准，其他字段不被覆盖。"""
    first = {"tracking_no": "SF9990000002", "student_id": "S2021005",
             "student_name": "赵六", "phone": "13800004005"}
    client.post("/api/packages/checkin", json=first)
    r = client.post("/api/packages/checkin", json={**first, "student_name": "钱七"})
    assert r.status_code == 200
    assert r.json()["created"] is False
    assert r.json()["package"]["student_name"] == "赵六"      # 首次信息未被覆盖
    conn = get_connection()
    n = conn.execute("SELECT COUNT(*) AS n FROM packages").fetchone()["n"]
    conn.close()
    assert n == 6                                             # 5 条 seed + 本次 1 条


def test_uc03_sequential_checkin_increments_shelf(client):
    """连续入库两件：入库序号 6/7 -> A-1-06-006、A-1-07-007。"""
    base = {"student_id": "S2021005", "student_name": "赵六"}
    c1 = client.post("/api/packages/checkin",
                     json={**base, "tracking_no": "SF9990000003"}).json()["pickup_code"]
    c2 = client.post("/api/packages/checkin",
                     json={**base, "tracking_no": "SF9990000004"}).json()["pickup_code"]
    assert c1 == "A-1-06-006"
    assert c2 == "A-1-07-007"


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


# ------------------------------------------------ UC-04 成员D 补充：异常与边界测试
#
# 上述用例覆盖了「授权码不存在 / 过期 / 已使用」三条 403/409 分支，
# 但仍有三处未被覆盖：授权码「存在但属于别的取件码」、异常件登记的入口校验、
# 以及 ttl 刚好为正的有效性下界。以下 5 个用例补齐这些分支。


def test_uc04_checkout_auth_code_belongs_to_another_package(client):
    """E3 的另一半：授权码真实存在但属于另一个取件码 -> 403，且不能误出库。

    原有用例只验证了「授权码完全不存在」（000000），没有验证「存在但不匹配」，
    而代码里 `auth["pickup_code"] != req.pickup_code` 是独立的一条判断。
    """
    other_auth = client.post("/api/packages/authorize", json={
        "pickup_code": OTHER, "delegate_name": "同学乙", "ttl_minutes": 30,
    }).json()["auth_code"]

    r = client.post("/api/packages/checkout", json={
        "pickup_code": CODE, "auth_code": other_auth, "operator": "值班员A",
    })
    assert r.status_code == 403
    assert "不匹配" in r.json()["detail"]

    # 失败必须不产生副作用：目标包裹仍在库，授权码也没被消耗
    q = client.get("/api/packages/lookup", params={"code": CODE})
    assert q.json()["packages"][0]["status"] == "in_stock"

    conn = get_connection()
    used = conn.execute(
        "SELECT used FROM authorizations WHERE auth_code=?", (other_auth,)
    ).fetchone()["used"]
    conn.close()
    assert used == 0

    # 该授权码仍可用于它真正对应的包裹
    ok = client.post("/api/packages/checkout", json={
        "pickup_code": OTHER, "auth_code": other_auth,
    })
    assert ok.status_code == 200
    assert ok.json()["auth_code_used"] == other_auth


def test_uc04_exception_on_nonexistent_code(client):
    """异常件登记的入口校验：查无此码 -> 404，且不留下脏数据。"""
    r = client.post("/api/packages/checkout", json={
        "pickup_code": "F-5-20-999", "report_exception": True,
        "note": "外包装破损", "operator": "值班员A",
    })
    assert r.status_code == 404
    assert "不存在" in r.json()["detail"]

    assert client.get("/api/packages/exceptions").json()["total"] == 0


def test_uc04_exception_on_picked_up_package(client):
    """缺陷回归：已出库包裹不得再登记异常件（否则状态机从 picked_up 回退到 exception）。"""
    client.post("/api/packages/checkout", json={"pickup_code": CODE})

    r = client.post("/api/packages/checkout", json={
        "pickup_code": CODE, "report_exception": True, "note": "事后补报破损",
    })
    assert r.status_code == 409
    assert "已出库" in r.json()["detail"]

    # 状态保持 picked_up，且出库时间没被清掉
    q = client.get("/api/packages/lookup", params={"code": CODE})
    assert q.json()["packages"][0]["status"] == "picked_up"
    assert q.json()["packages"][0]["picked_up_at"] is not None
    assert client.get("/api/packages/exceptions").json()["total"] == 0


def test_uc04_exception_duplicate(client):
    """缺陷回归：同一包裹重复登记异常件 -> 409，异常件清单只有 1 条。"""
    first = client.post("/api/packages/checkout", json={
        "pickup_code": CODE, "report_exception": True,
        "note": "外包装破损", "operator": "值班员A",
    })
    assert first.status_code == 200

    second = client.post("/api/packages/checkout", json={
        "pickup_code": CODE, "report_exception": True, "note": "再次登记",
    })
    assert second.status_code == 409
    assert "重复登记" in second.json()["detail"]

    lst = client.get("/api/packages/exceptions").json()
    assert lst["total"] == 1
    assert lst["exceptions"][0]["reason"] == "外包装破损"


def test_uc04_authorize_ttl_boundary_one_minute(client):
    """边界：ttl_minutes=1 是「仍然有效」的下界（紧邻 ttl=0 的立即过期）。"""
    r = client.post("/api/packages/authorize", json={
        "pickup_code": CODE, "delegate_name": "同学甲", "ttl_minutes": 1,
    })
    assert r.status_code == 200
    auth = r.json()["auth_code"]

    q = client.get(f"/api/packages/authorize/{CODE}").json()
    assert q["valid"] is True
    assert q["active_authorization"]["expired"] is False
    assert q["active_authorization"]["auth_code"] == auth

    ok = client.post("/api/packages/checkout", json={
        "pickup_code": CODE, "auth_code": auth,
    })
    assert ok.status_code == 200
    assert ok.json()["auth_code_used"] == auth
