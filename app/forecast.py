"""高峰期排队预测算法（UC-02），全部为纯函数，便于单元测试。

== 输入 ==
pending_count    当前待取件包裹数（= 在库包裹数），近似为排队人数
history          {hour(0-23): avg_service_minutes} 历史各时段平均单人取件时长
current_hour     当前小时（0-23）
servers          同时开放的取件窗口数（默认 2）
default_service  完全无历史数据时的兜底单人时长（默认 1.5 分钟）

== 算法 ==
1) service = 当前时段的历史平均时长；
   若该时段无数据或值为 NULL（采集缺失），退化为全部历史时段的算术平均；
   若完全没有可用历史数据，使用 default_service（1.5 分钟）。
2) predicted_wait = ceil(pending_count * service / servers)
   —— 工作量模型：待服务总工作量 / 并行窗口数，向上取整到分钟。
   pending_count <= 0 时直接返回 0（无人排队边界）。
3) 拥挤等级：wait<=2 空闲；wait<=5 正常；wait<=10 繁忙；wait>10 高峰。
4) 推荐错峰时段：在历史时段中挑平均服务时长最低、且不等于当前小时的时段；
   无历史数据时给出基于经验的固定建议（10:00 与 15:00）。

设计取舍：课程项目不引入排队论仿真，用可解释、可复现的确定性公式，
保证同一输入必然得到同一输出，方便断言与 CI。
"""
from __future__ import annotations

import math
from typing import Dict, Optional

DEFAULT_SERVICE_MINUTES = 1.5
DEFAULT_SERVERS = 2
DEFAULT_OFFPEAK_HOURS = [10, 15]


def average_service_minutes(
    history: Optional[Dict], current_hour: int, default: float = DEFAULT_SERVICE_MINUTES
) -> float:
    """取当前时段平均服务时长；缺该时段或值为 NULL 用全局平均；完全无数据用兜底值。

    注意：NULL 必须先判再取值，否则 float(None) 会抛 TypeError，接口会变成 500。
    """
    if not history:
        return float(default)
    value = history.get(current_hour)
    if value is not None:
        return float(value)
    values = [float(v) for v in history.values() if v is not None]
    if not values:
        return float(default)
    return sum(values) / len(values)


def predict_wait_minutes(
    pending_count: int, service_minutes: float, servers: int = DEFAULT_SERVERS
) -> int:
    """等待分钟数 = ceil(pending_count * service_minutes / servers)。"""
    if pending_count is None or pending_count <= 0:
        return 0
    if servers <= 0:
        servers = 1
    if service_minutes <= 0:
        return 0
    return int(math.ceil(pending_count * service_minutes / servers))


def congestion_level(wait_minutes: int) -> str:
    """按等待分钟数划分拥挤等级。"""
    if wait_minutes <= 2:
        return "空闲"
    if wait_minutes <= 5:
        return "正常"
    if wait_minutes <= 10:
        return "繁忙"
    return "高峰"


def recommend_offpeak_hour(
    history: Optional[Dict], current_hour: int, fallback=None
) -> int:
    """推荐历史平均服务时长最低的非当前时段；无历史则用经验错峰时段。"""
    fallback = fallback or DEFAULT_OFFPEAK_HOURS
    if history:
        candidates = [
            (int(h), float(v))
            for h, v in history.items()
            if v is not None and int(h) != current_hour
        ]
        if candidates:
            return min(candidates, key=lambda kv: (kv[1], kv[0]))[0]
    for h in fallback:
        if h != current_hour:
            return h
    return fallback[0] if fallback else current_hour


def forecast(
    pending_count: int,
    history: Optional[Dict],
    current_hour: int,
    servers: int = DEFAULT_SERVERS,
    default: float = DEFAULT_SERVICE_MINUTES,
) -> Dict:
    """组装完整预测结果（API 直接返回本函数结果）。"""
    service = average_service_minutes(history, current_hour, default)
    wait = predict_wait_minutes(pending_count, service, servers)
    offpeak = recommend_offpeak_hour(history, current_hour)
    level = congestion_level(wait)
    return {
        "current_hour": current_hour,
        "pending_count": pending_count,
        "servers": servers,
        "avg_service_minutes": round(service, 2),
        "predicted_wait_minutes": wait,
        "congestion_level": level,
        "recommended_offpeak_hour": offpeak,
        "recommendation": (
            f"当前预计等待 {wait} 分钟（{level}），"
            f"建议 {offpeak:02d}:00-{offpeak:02d}:59 错峰取件。"
        ),
        "algorithm": (
            "wait = ceil(pending_count * avg_service_minutes / servers); "
            "avg 取当前时段历史均值，无该时段取全局均值，完全无历史取 1.5min"
        ),
    }
