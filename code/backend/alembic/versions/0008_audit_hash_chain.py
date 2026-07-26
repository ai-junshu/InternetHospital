"""add plat_audit_log hash chain columns (P4 审计哈希链防篡改)

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-26

- seq_no：单调递增序号（索引）
- prev_hash：上一条记录的 hash（链式挂接）
- hash：本条内容 SHA-256（索引，供快速校验）
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "plat_audit_log",
        sa.Column("seq_no", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "plat_audit_log",
        sa.Column("prev_hash", sa.String(64), server_default="", nullable=False),
    )
    op.add_column(
        "plat_audit_log",
        sa.Column("hash", sa.String(64), server_default="", nullable=False),
    )
    op.create_index("ix_plat_audit_log_seq_no", "plat_audit_log", ["seq_no"])
    op.create_index("ix_plat_audit_log_hash", "plat_audit_log", ["hash"])


def downgrade() -> None:
    op.drop_index("ix_plat_audit_log_hash", table_name="plat_audit_log")
    op.drop_index("ix_plat_audit_log_seq_no", table_name="plat_audit_log")
    op.drop_column("plat_audit_log", "hash")
    op.drop_column("plat_audit_log", "prev_hash")
    op.drop_column("plat_audit_log", "seq_no")
