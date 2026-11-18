"""FastAPI 应用入口：注册 4 个 UC 路由分组、CORS、启动建表。

启动：uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db
from .routers import uc01_lookup, uc02_forecast, uc03_checkin, uc04_checkout


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时自动建表并在空库时写入演示包裹数据
    init_db()
    yield


app = FastAPI(
    title="校园快递驿站智能取件助手 API",
    version="1.0.0",
    description="高级软件工程课程项目：4 个核心用例 / 4 个 API 分组",
    lifespan=lifespan,
)

# 前端用 python -m http.server 独立端口打开，需允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(uc01_lookup.router)
app.include_router(uc02_forecast.router)
app.include_router(uc03_checkin.router)
app.include_router(uc04_checkout.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "campus-express", "version": "1.0.0"}


@app.get("/")
def root():
    return {
        "message": "校园快递驿站智能取件助手 API",
        "docs": "/docs",
        "health": "/api/health",
    }


# 模块级再幂等初始化一次：保证以任何方式（含不带 with 的 TestClient）访问时表都存在
init_db()
