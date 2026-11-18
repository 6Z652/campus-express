"""请求体模型（Pydantic）。字段缺失/类型错误由 FastAPI 自动返回 422。"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class CheckinRequest(BaseModel):
    tracking_no: str
    student_id: str
    student_name: str
    phone: str = ""
    size: str = "medium"


class AuthorizeRequest(BaseModel):
    pickup_code: str
    delegate_name: str
    delegate_phone: str = ""
    ttl_minutes: int = 30


class CheckoutRequest(BaseModel):
    pickup_code: str
    auth_code: Optional[str] = None
    operator: str = ""
    note: str = ""
    report_exception: bool = False
