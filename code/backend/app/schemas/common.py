"""通用 Schema（分页/统一响应复用，技术架构第10.2章）。"""
from datetime import datetime
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict

from app.core.response import ApiResponse

T = TypeVar("T")


class BaseOut(BaseModel):
    """ORM 基类输出（含 id / 时间戳）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PageResult(BaseModel, Generic[T]):
    total: int = 0
    page: int = 1
    page_size: int = 20
    items: list[T] = []
