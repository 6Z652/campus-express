"""SQLite 建表、演示数据 seed 与连接管理（仅标准库 sqlite3，零外部服务）。

数据文件默认位于 data/express.db；可通过环境变量 EXPRESS_DB_PATH 覆盖，
单元测试正是借此把数据隔离到系统临时目录，避免污染演示库。
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "data", "express.db")
DB_PATH = os.environ.get("EXPRESS_DB_PATH", DEFAULT_DB_PATH)

SCHEMA = """
CREATE TABLE IF NOT EXISTS packages (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    tracking_no   TEXT NOT NULL UNIQUE,
    student_id    TEXT NOT NULL,
    student_name  TEXT NOT NULL,
    phone         TEXT DEFAULT '',
    size          TEXT DEFAULT 'medium',
    area          TEXT NOT NULL,
    level         INTEGER NOT NULL,
    slot          INTEGER NOT NULL,
    shelf_label   TEXT NOT NULL,
    pickup_code   TEXT NOT NULL UNIQUE,
    status        TEXT NOT NULL DEFAULT 'in_stock',
    created_at    TEXT NOT NULL,
    picked_up_at  TEXT
);
CREATE TABLE IF NOT EXISTS queue_history (
    hour                 INTEGER PRIMARY KEY,
    avg_service_minutes  REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS authorizations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pickup_code     TEXT NOT NULL,
    delegate_name   TEXT NOT NULL,
    delegate_phone  TEXT DEFAULT '',
    auth_code       TEXT NOT NULL UNIQUE,
    expires_at      TEXT NOT NULL,
    used            INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS exceptions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    pickup_code   TEXT NOT NULL,
    tracking_no   TEXT,
    reason        TEXT NOT NULL,
    operator      TEXT DEFAULT '',
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_packages_student ON packages(student_id);
CREATE INDEX IF NOT EXISTS idx_auth_pickup     ON authorizations(pickup_code);
"""

DROP_SCHEMA = """
DROP TABLE IF EXISTS packages;
DROP TABLE IF EXISTS queue_history;
DROP TABLE IF EXISTS authorizations;
DROP TABLE IF EXISTS exceptions;
"""

# 演示包裹：学生 S2021001「张三」有 3 个包裹，用于验证 UC-01 的同学生聚合查询
SEED_PACKAGES = [
    ("SF1000000001", "S2021001", "张三", "13800001001", "small"),
    ("SF1000000002", "S2021001", "张三", "13800001001", "medium"),
    ("SF1000000003", "S2021001", "张三", "13800001001", "large"),
    ("YT2000000001", "S2021002", "李四", "13800002002", "small"),
    ("JD3000000001", "S2021003", "王五", "13800003003", "medium"),
]

# 历史各时段平均单人取件时长（分钟）：12 点午休为高峰，10 点/15 点为低峰
SEED_HISTORY = {
    8: 0.8, 9: 1.0, 10: 0.7, 11: 1.6, 12: 3.2, 13: 2.8, 14: 1.4,
    15: 0.9, 16: 1.1, 17: 2.0, 18: 2.6, 19: 1.3, 20: 0.8,
}


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _seed(conn: sqlite3.Connection) -> None:
    from .codes import make_pickup_code, shelf_position

    now = datetime.now().isoformat(timespec="seconds")
    for i, (tracking_no, sid, name, phone, size) in enumerate(SEED_PACKAGES, start=1):
        pos = shelf_position(i)
        code = make_pickup_code(i, pos)
        conn.execute(
            "INSERT INTO packages "
            "(tracking_no, student_id, student_name, phone, size, area, level, slot, "
            " shelf_label, pickup_code, status, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,'in_stock',?)",
            (
                tracking_no, sid, name, phone, size,
                pos["area"], pos["level"], pos["slot"], pos["label"], code, now,
            ),
        )
    conn.executemany(
        "INSERT INTO queue_history (hour, avg_service_minutes) VALUES (?,?)",
        list(SEED_HISTORY.items()),
    )


def init_db(reset: bool = False) -> None:
    """启动/测试时调用：建表 + 仅在空库时写入演示数据（幂等）。"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    try:
        if reset:
            conn.executescript(DROP_SCHEMA)
        conn.executescript(SCHEMA)
        n = conn.execute("SELECT COUNT(*) AS n FROM packages").fetchone()["n"]
        if n == 0:
            _seed(conn)
        conn.commit()
    finally:
        conn.close()


def reset_db() -> None:
    """彻底重建演示库（测试 fixture 与 smoke 脚本用，保证结果可复现）。"""
    init_db(reset=True)
