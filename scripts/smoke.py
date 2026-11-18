"""API 冒烟脚本：用 TestClient 依次调用全部 API，打印每个接口的真实响应 JSON。

用法（项目根目录）： python scripts/smoke.py

说明：
- 不启动任何常驻后台服务，TestClient 在 with 块结束后自动关闭。
- 每次运行先 reset_db() 重建演示库，保证输出可复现。
- collect() 返回结构化结果，供 scripts/collect_metrics.py 采集真实响应示例。
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault("EXPRESS_DB_PATH", os.path.join(ROOT, "data", "express.db"))


def collect():
    """依次调用全部 API，返回每一步的真实结果（不打印）。"""
    from fastapi.testclient import TestClient

    from app.db import reset_db
    from app.main import app

    reset_db()
    steps = []

    with TestClient(app) as c:
        def call(name, method, path, body=None):
            if body is None:
                r = c.request(method, path)
            else:
                r = c.request(method, path, json=body)
            try:
                resp = r.json()
            except Exception:
                resp = r.text
            step = {
                "name": name,
                "api": f"{method} {path}",
                "method": method,
                "path": path,
                "request_body": body,
                "status_code": r.status_code,
                "ok": 200 <= r.status_code < 300,
                "response": resp,
            }
            steps.append(step)
            return resp

        # ---- 基础 ----
        call("健康检查", "GET", "/api/health")
        call("根路径", "GET", "/")

        # ---- UC-01 取件码解析与包裹聚合 ----
        call("UC-01 取件码查询(GET)", "GET", "/api/packages/lookup?code=A-1-01-001")
        call("UC-01 取件码查询(POST)", "POST", "/api/packages/lookup?code=A-1-01-001")
        call("UC-01 非法格式", "GET", "/api/packages/lookup?code=bad-code")
        call("UC-01 取件码不存在", "GET", "/api/packages/lookup?code=F-5-20-999")

        # ---- UC-02 排队预测 ----
        call("UC-02 排队预测", "GET", "/api/queue/forecast")

        # ---- UC-03 入库与货架分配 ----
        checkin_body = {
            "tracking_no": "SF9990000001",
            "student_id": "S2021004",
            "student_name": "赵六",
            "phone": "13800004004",
            "size": "large",
        }
        new = call("UC-03 扫码入库", "POST", "/api/packages/checkin", checkin_body)
        new_code = new["pickup_code"]
        call("UC-03 重复入库(幂等)", "POST", "/api/packages/checkin", checkin_body)
        call("UC-01 查询新入库包裹", "GET", f"/api/packages/lookup?code={new_code}")

        # ---- UC-04 出库核验与代取授权 ----
        auth_body = {
            "pickup_code": "A-1-01-001",
            "delegate_name": "同学甲",
            "delegate_phone": "13800000000",
            "ttl_minutes": 30,
        }
        auth = call("UC-04 生成代取授权", "POST", "/api/packages/authorize", auth_body)
        auth_code = auth["auth_code"]
        call("UC-04 查询授权状态", "GET", "/api/packages/authorize/A-1-01-001")
        call("UC-04 重复授权(拒绝)", "POST", "/api/packages/authorize", auth_body)
        call("UC-04 错误授权码出库", "POST", "/api/packages/checkout", {
            "pickup_code": "A-1-01-001", "auth_code": "000000", "operator": "值班员A",
        })
        call("UC-04 代取出库", "POST", "/api/packages/checkout", {
            "pickup_code": "A-1-01-001", "auth_code": auth_code, "operator": "值班员A",
        })
        call("UC-04 重复出库(拒绝)", "POST", "/api/packages/checkout", {
            "pickup_code": "A-1-01-001", "operator": "值班员A",
        })

        expired = call("UC-04 生成过期授权(ttl=0)", "POST", "/api/packages/authorize", {
            "pickup_code": "A-1-02-002", "delegate_name": "同学乙", "ttl_minutes": 0,
        })
        call("UC-04 过期授权出库(拒绝)", "POST", "/api/packages/checkout", {
            "pickup_code": "A-1-02-002", "auth_code": expired["auth_code"],
        })

        call("UC-04 登记异常件", "POST", "/api/packages/checkout", {
            "pickup_code": "A-1-03-003", "operator": "值班员A",
            "note": "外包装破损，暂停出库", "report_exception": True,
        })
        call("UC-04 异常件清单", "GET", "/api/packages/exceptions")
        call("UC-04 查询未授权包裹", "GET", "/api/packages/authorize/A-1-04-004")
        call("UC-04 对不存在取件码授权", "POST", "/api/packages/authorize", {
            "pickup_code": "F-5-20-999", "delegate_name": "同学丙",
        })

    return steps


def main():
    steps = collect()
    print("=" * 78)
    print("校园快递驿站智能取件助手 - API 冒烟测试（TestClient 真实调用）")
    print("=" * 78)
    print(f"共调用 {len(steps)} 个接口步骤\n")
    for i, s in enumerate(steps, start=1):
        print(f"[{i:02d}] {s['name']}")
        print(f"     API     : {s['api']}")
        if s["request_body"] is not None:
            print("     request : " + json.dumps(s["request_body"], ensure_ascii=False))
        else:
            print("     request : -")
        print(f"     status  : {s['status_code']}")
        print("     response: " + json.dumps(s["response"], ensure_ascii=False, indent=2))
        print("-" * 78)
    ok = sum(1 for s in steps if s["ok"])
    print(f"完成：{len(steps)} 次调用，2xx={ok}，非 2xx={len(steps) - ok}")
    return steps


if __name__ == "__main__":
    main()
