"""add ih_order.prescription_id column

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-01

补 sprint 阶段在 IhOrder 模型层新增、但迁移遗漏的 prescription_id 列
（处方药凭方购买 R4 合规链路依赖）。
"""
import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    exists = bind.execute(
        sa.text(
            "select 1 from information_schema.columns "
            "where table_name='ih_order' and column_name='prescription_id'"
        )
    ).first()
    if not exists:
        op.add_column(
            "ih_order",
            sa.Column("prescription_id", sa.Integer(), nullable=True, index=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    exists = bind.execute(
        sa.text(
            "select 1 from information_schema.columns "
            "where table_name='ih_order' and column_name='prescription_id'"
        )
    ).first()
    if exists:
        op.drop_column("ih_order", "prescription_id")
