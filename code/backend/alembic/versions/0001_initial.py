"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-25

首版迁移：建出全部 ih_/mt_/plat_ 表结构（技术架构第11.2章），不灌数据。
后续增量变更新增独立 migration 文件；本文件使用 Base.metadata.create_all 一次性建表。
"""
from alembic import op

from app import models  # noqa: F401 确保表已注册
from app.models.base import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
