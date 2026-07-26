"""add plat_account + ih_prescription_item 剂量列（P4 安全闭环 / 风险3修复）

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-26

- plat_account：后台账号密码登录（platform/xingyao/store/therapist），
  密码经 PBKDF2-HMAC-SHA256 加盐哈希落库（core.security.hash_password）。
- ih_prescription_item.daily_dose / max_daily_dose：处方明细单日用量与上限，
  供合理用药引擎剂量告警落库（风险3：开方未传剂量）。
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plat_account",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=True),
        sa.Column("password_hash", sa.String(128), nullable=False),
        sa.Column("password_salt", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column("two_factor_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.add_column(
        "ih_prescription_item",
        sa.Column("daily_dose", sa.Float(), nullable=True),
    )
    op.add_column(
        "ih_prescription_item",
        sa.Column("max_daily_dose", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ih_prescription_item", "max_daily_dose")
    op.drop_column("ih_prescription_item", "daily_dose")
    op.drop_table("plat_account")
