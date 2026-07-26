"""add plat_account.totp_secret (P4 双因子 TOTP 密钥落库)

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "plat_account",
        sa.Column("totp_secret", sa.String(64), server_default="", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("plat_account", "totp_secret")
