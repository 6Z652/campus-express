"""UC-02 高峰期排队预测与错峰提醒。

GET /api/queue/forecast
  待取件数 = SELECT COUNT(*) FROM packages WHERE status='in_stock'
  历史时段均值来自 queue_history 表，具体算法见 app/forecast.py。
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

from ..db import get_connection
from ..forecast import forecast as compute_forecast

router = APIRouter(prefix="/api/queue", tags=["UC-02 高峰期排队预测与错峰提醒"])


@router.get("/forecast")
def queue_forecast():
    conn = get_connection()
    try:
        pending = conn.execute(
            "SELECT COUNT(*) AS n FROM packages WHERE status='in_stock'"
        ).fetchone()["n"]
        history = {
            r["hour"]: r["avg_service_minutes"]
            for r in conn.execute(
                "SELECT hour, avg_service_minutes FROM queue_history"
            ).fetchall()
        }
    finally:
        conn.close()

    return compute_forecast(pending, history, datetime.now().hour)
