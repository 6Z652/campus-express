"""UC-02 预测算法边界测试：0 人排队、高峰、无历史数据等。

forecast.py 全是纯函数，本文件不依赖 TestClient / 数据库。
"""
from __future__ import annotations

from app.forecast import (
    DEFAULT_SERVICE_MINUTES,
    DEFAULT_SERVERS,
    average_service_minutes,
    congestion_level,
    forecast,
    predict_wait_minutes,
    recommend_offpeak_hour,
)

HISTORY = {
    8: 0.8, 9: 1.0, 10: 0.7, 11: 1.6, 12: 3.2, 13: 2.8, 14: 1.4,
    15: 0.9, 16: 1.1, 17: 2.0, 18: 2.6, 19: 1.3, 20: 0.8,
}


# ---------------------------------------------------------------- 0 人排队

def test_zero_queue_returns_zero_wait():
    assert predict_wait_minutes(0, 3.2) == 0
    r = forecast(0, HISTORY, 12)
    assert r["pending_count"] == 0
    assert r["predicted_wait_minutes"] == 0
    assert r["congestion_level"] == "空闲"


def test_negative_queue_is_treated_as_zero():
    assert predict_wait_minutes(-5, 2.0) == 0


# ---------------------------------------------------------------- 高峰

def test_peak_hour_prediction():
    """12 点历史均值 3.2min，20 人排队、2 个窗口 -> ceil(20*3.2/2)=32 分钟。"""
    r = forecast(20, HISTORY, 12)
    assert r["avg_service_minutes"] == 3.2
    assert r["predicted_wait_minutes"] == 32
    assert r["congestion_level"] == "高峰"
    assert r["servers"] == DEFAULT_SERVERS == 2


def test_peak_prediction_is_monotonic_with_queue():
    short = forecast(2, HISTORY, 12)["predicted_wait_minutes"]
    long = forecast(20, HISTORY, 12)["predicted_wait_minutes"]
    assert long > short


# ---------------------------------------------------------------- 无历史数据

def test_no_history_uses_default_service():
    r = forecast(10, {}, 12)
    assert r["avg_service_minutes"] == DEFAULT_SERVICE_MINUTES == 1.5
    assert r["predicted_wait_minutes"] == 8        # ceil(10*1.5/2)
    assert r["recommended_offpeak_hour"] == 10      # 经验错峰时段


def test_none_history_uses_default_service():
    r = forecast(4, None, 10)
    assert r["avg_service_minutes"] == 1.5
    assert r["predicted_wait_minutes"] == 3        # ceil(4*1.5/2)
    assert r["recommended_offpeak_hour"] == 15


def test_average_service_missing_hour_falls_back_to_global_mean():
    assert average_service_minutes({10: 1.0, 12: 3.0}, 22) == 2.0


# ---------------------------------------------------------------- 其他边界

def test_zero_service_minutes_returns_zero():
    assert predict_wait_minutes(10, 0) == 0


def test_zero_servers_is_guarded():
    assert predict_wait_minutes(4, 2.0, servers=0) == 8


def test_congestion_level_boundaries():
    assert congestion_level(2) == "空闲"
    assert congestion_level(3) == "正常"
    assert congestion_level(5) == "正常"
    assert congestion_level(6) == "繁忙"
    assert congestion_level(10) == "繁忙"
    assert congestion_level(11) == "高峰"


def test_recommend_offpeak_picks_lowest_non_current_hour():
    assert recommend_offpeak_hour(HISTORY, 12) == 10   # 10 点 0.7 最低
    assert recommend_offpeak_hour(HISTORY, 10) == 8    # 排除当前 10 点，0.8 并列取小时较小者


def test_recommend_offpeak_no_history():
    assert recommend_offpeak_hour({}, 10) == 15
    assert recommend_offpeak_hour(None, 15) == 10


# ---------------------------------------------------------------- E8 / E9（本轮补充）

def test_history_hour_value_none_falls_back_to_global_mean():
    """E8：历史表当前时段值为 NULL 时，按「无该时段数据」回退，不得抛 TypeError。

    真实库里 queue_history.avg_service_minutes 允许采集缺失写 NULL；
    若先 float(history[current_hour]) 再判空，接口会直接 500。
    """
    history = {10: 1.0, 11: None, 12: 3.0}
    assert average_service_minutes(history, 11) == 2.0        # (1.0+3.0)/2
    r = forecast(6, history, 11)
    assert r["avg_service_minutes"] == 2.0
    assert r["predicted_wait_minutes"] == 6                   # ceil(6*2.0/2)
    assert r["recommended_offpeak_hour"] == 10                # 跳过 NULL 的 11 点


def test_nonzero_queue_never_reports_zero_wait():
    """E9：只要有人排队，等待分钟数向上取整后至少为 1，不得显示 0 分钟。"""
    assert predict_wait_minutes(1, 0.2) == 1                  # ceil(0.1)
    assert predict_wait_minutes(1, 0.5, servers=3) == 1        # ceil(0.1667)
    r = forecast(1, HISTORY, 10)
    assert r["predicted_wait_minutes"] == 1
    assert r["congestion_level"] == "空闲"


def test_forecast_is_deterministic():
    assert forecast(20, HISTORY, 12) == forecast(20, HISTORY, 12)
