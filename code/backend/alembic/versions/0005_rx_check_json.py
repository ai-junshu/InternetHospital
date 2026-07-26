"""add ih_prescription.rx_check_json

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-26

合理用药引擎（第14章第三方对接）前置校验结果入库：冲突/禁忌/剂量告警，
以及降级标记。JSON 列，无需预设结构，兼容 mock 与真实供应商返回。
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ih_prescription",
        sa.Column("rx_check_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ih_prescription", "rx_check_json")
