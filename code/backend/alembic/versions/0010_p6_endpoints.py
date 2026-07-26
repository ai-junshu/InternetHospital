"""add P6 endpoint tables

Revision ID: 0010
Revises: 0009_encrypt_secret_and_health_tags
Create Date: 2026-07-26

P6 后端端点补齐：医生排班 / 药品目录 / 调理师排班 / 调理师标签 / 合规采集审核。
仅创建增量表，复用 create_all 的 checkfirst 避免重复建表。
"""
from alembic import op

from app import models  # noqa: F401 确保表已注册
from app.models.base import Base
from app.models.ih_models import IhDoctorSchedule, IhDrug
from app.models.mt_models import MtTherapistSchedule, MtTherapistTag, MtTherapistTagRel
from app.models.plat_models import PlatComplianceItem

revision = "0010"
down_revision = "0009_encrypt_secret_and_health_tags"
branch_labels = None
depends_on = None

_P6_TABLES = [
    IhDoctorSchedule.__table__,
    IhDrug.__table__,
    MtTherapistSchedule.__table__,
    MtTherapistTag.__table__,
    MtTherapistTagRel.__table__,
    PlatComplianceItem.__table__,
]


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, tables=_P6_TABLES)


def downgrade() -> None:
    bind = op.get_bind()
    for table in reversed(_P6_TABLES):
        table.drop(bind=bind, checkfirst=True)
