"""create ih_department table

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-01

P3 业务闭环：科室结构（PRD 3.3 医院管理，组织管理维度）。
幂等建表：已存在则跳过。
"""
import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

_TABLE = "ih_department"


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
        "ih_department",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("head", sa.String(64), nullable=True),
        sa.Column("remark", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=True, server_default=sa.false()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ih_department_name", "ih_department", ["name"])


def downgrade() -> None:
    bind = op.get_bind()
    if not _exists(bind):
        return
    op.drop_index("ix_ih_department_name", table_name="ih_department")
    op.drop_table("ih_department")
