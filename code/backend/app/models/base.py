"""ORM 公共基类（技术架构第11.1章命名规范）。

所有业务表继承 TimestampMixin，统一字段：
- id（主键自增）
- created_at / updated_at
- is_deleted（逻辑删除）
表名严格采用 ih_ / mt_ / plat_ 前缀（见各分域模型）。
"""
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
