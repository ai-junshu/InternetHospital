"""make plat_model_pred_log.model_id nullable

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-26

AI 反馈闭环（第15.4章）：预测日志由业务回写产生，此时往往尚无对应
plat_ai_model 行，故将 model_id 改为可空，避免外键/非空约束阻断落库。
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "plat_model_pred_log",
        "model_id",
        existing_type=sa.INTEGER(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "plat_model_pred_log",
        "model_id",
        existing_type=sa.INTEGER(),
        nullable=False,
    )
