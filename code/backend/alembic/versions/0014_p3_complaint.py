"""create ih_complaint table

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-01

P3 业务闭环：投诉与售后（PRD 3.3.4 患者权益闭环）。
幂等建表：已存在则跳过。
"""
import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

_TABLE = "ih_complaint"


def _exists(bind) -> bool:
    return bool(
        bind.execute(
            sa.text("select 1 from information_schema.tables where table_name=:t"),
            {"t": _TABLE},
        ).first()
    )


def upgrade() -> None:
    bind = op.get_bind()
    if _exists(bind):
        return
    op.create_table(
        "ih_complaint",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(16), nullable=False, server_default="service"),
        sa.Column("content", sa.String(1024), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("reply", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=True, server_default=sa.false()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ih_complaint_order_id", "ih_complaint", ["order_id"])
    op.create_index("ix_ih_complaint_user_id", "ih_complaint", ["user_id"])
    op.create_index("ix_ih_complaint_status", "ih_complaint", ["status"])


def downgrade() -> None:
    bind = op.get_bind()
    if not _exists(bind):
        return
    op.drop_index("ix_ih_complaint_status", table_name="ih_complaint")
    op.drop_index("ix_ih_complaint_user_id", table_name="ih_complaint")
    op.drop_index("ix_ih_complaint_order_id", table_name="ih_complaint")
    op.drop_table("ih_complaint")
