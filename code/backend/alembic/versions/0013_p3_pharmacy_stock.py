"""create ih_pharmacy and ih_drug_stock tables

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-01

P3 业务闭环：合作药房与药品库存（PRD 3.3.2 药房管理）。
幂等建表：已存在则跳过。
"""
import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

_TABLES = ("ih_pharmacy", "ih_drug_stock")


def _exists(bind, table: str) -> bool:
    return bool(
        bind.execute(
            sa.text("select 1 from information_schema.tables where table_name=:t"),
            {"t": table},
        ).first()
    )


def upgrade() -> None:
    bind = op.get_bind()
    if not _exists(bind, "ih_pharmacy"):
        op.create_table(
            "ih_pharmacy",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("region", sa.String(64), nullable=True),
            sa.Column("license_no", sa.String(64), nullable=True),
            sa.Column("contact", sa.String(64), nullable=True),
            sa.Column("status", sa.String(16), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("is_deleted", sa.Boolean(), nullable=True, server_default=sa.false()),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_ih_pharmacy_name", "ih_pharmacy", ["name"])
    if not _exists(bind, "ih_drug_stock"):
        op.create_table(
            "ih_drug_stock",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("drug_id", sa.Integer(), sa.ForeignKey("ih_drug.id"), nullable=False),
            sa.Column("pharmacy_id", sa.Integer(), sa.ForeignKey("ih_pharmacy.id"), nullable=False),
            sa.Column("stock", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("safety_stock", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("is_deleted", sa.Boolean(), nullable=True, server_default=sa.false()),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_ih_drug_stock_drug_id", "ih_drug_stock", ["drug_id"])
        op.create_index("ix_ih_drug_stock_pharmacy_id", "ih_drug_stock", ["pharmacy_id"])
        op.create_index(
            "uq_ih_drug_stock_drug_pharmacy",
            "ih_drug_stock",
            ["drug_id", "pharmacy_id"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _exists(bind, "ih_drug_stock"):
        op.drop_index("uq_ih_drug_stock_drug_pharmacy", table_name="ih_drug_stock")
        op.drop_index("ix_ih_drug_stock_pharmacy_id", table_name="ih_drug_stock")
        op.drop_index("ix_ih_drug_stock_drug_id", table_name="ih_drug_stock")
        op.drop_table("ih_drug_stock")
    if _exists(bind, "ih_pharmacy"):
        op.drop_index("ix_ih_pharmacy_name", table_name="ih_pharmacy")
        op.drop_table("ih_pharmacy")
