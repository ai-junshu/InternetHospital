"""create ih_pharmacist table

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-01

药师档案表（迭代 A · S1 双身份登录 / S2 药师审核工作台）。
role=pharmacist 的 JWT 关联到本表记录，满足等保三级"审方责任到人、身份可追溯"。
幂等建表：已存在则跳过。
"""
import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    exists = bind.execute(
        sa.text("select 1 from information_schema.tables where table_name='ih_pharmacist'")
    ).first()
    if exists:
        return
    op.create_table(
        "ih_pharmacist",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("ih_user.id"), nullable=False),
        sa.Column("license_no", sa.String(64), nullable=False),
        sa.Column("title", sa.String(32), nullable=True),
        sa.Column("pharmacy_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=True, server_default=sa.false()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ih_pharmacist_user_id", "ih_pharmacist", ["user_id"])
    op.create_index(
        "ix_ih_pharmacist_license_no", "ih_pharmacist", ["license_no"], unique=True
    )


def downgrade() -> None:
    bind = op.get_bind()
    exists = bind.execute(
        sa.text("select 1 from information_schema.tables where table_name='ih_pharmacist'")
    ).first()
    if not exists:
        return
    op.drop_index("ix_ih_pharmacist_license_no", table_name="ih_pharmacist")
    op.drop_index("ix_ih_pharmacist_user_id", table_name="ih_pharmacist")
    op.drop_table("ih_pharmacist")
