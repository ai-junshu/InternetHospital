"""add mt_risk_profile table

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-25

新增健康风险画像表 mt_risk_profile（PRD 3.2 健康数据中台 / 第15.4章 AI 反馈闭环）。
仅创建增量表，复用 create_all 的 checkfirst 避免重复建表。
"""
from alembic import op

from app import models  # noqa: F401 确保表已注册
from app.models.base import Base
from app.models.mt_models import MtRiskProfile

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, tables=[MtRiskProfile.__table__])


def downgrade() -> None:
    bind = op.get_bind()
    MtRiskProfile.__table__.drop(bind=bind, checkfirst=True)
