"""add consultation tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-25

新增在线复诊会话表 ih_consultation、会话消息表 ih_consultation_message（PRD 3.1.3-3.1.4）。
仅创建增量表，复用 create_all 的 checkfirst 避免重复建表。
"""
from alembic import op

from app import models  # noqa: F401 确保表已注册
from app.models.base import Base
from app.models.ih_models import IhConsultation, IhConsultationMessage

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(
        bind=bind, tables=[IhConsultation.__table__, IhConsultationMessage.__table__]
    )


def downgrade() -> None:
    bind = op.get_bind()
    IhConsultation.__table__.drop(bind=bind, checkfirst=True)
    IhConsultationMessage.__table__.drop(bind=bind, checkfirst=True)
