"""测试夹具：把数据库隔离到系统临时目录，每个用例前重建干净演示数据。

关键：必须在 import app.* 之前设置 EXPRESS_DB_PATH，否则 db.py 会绑定默认演示库。
"""
from __future__ import annotations

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

TEST_DB = os.path.join(tempfile.gettempdir(), "campus_express_test.db")
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)
os.environ["EXPRESS_DB_PATH"] = TEST_DB

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import reset_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    """每个测试前重建表并重新 seed，保证用例互不依赖、结果可复现。"""
    reset_db()
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
