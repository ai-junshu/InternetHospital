"""encrypt plat_account.totp_secret (KMS envelope) and mt_customer.health_tags (field encryption)

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-26

- plat_account.totp_secret: VARCHAR(64) -> TEXT，既有明文经本地 KMS 信封加密重写入。
- mt_customer.health_tags: JSON -> TEXT（USING 转文本），既有 JSON 经字段级加密重写入。
- 幂等：已加密（looks_encrypted）或空值行跳过，可重复执行。迁移前请备份 DB。
- 解密用同一 KMS 可逆（见 downgrade）。
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

from app.core.kms import get_kms, looks_encrypted

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def _reencrypt(table: str, column: str, bind) -> None:
    kms = get_kms()
    rows = bind.execute(text(f"SELECT id, {column} FROM {table}")).fetchall()
    for row in rows:
        raw = row[1]
        if raw is None or raw == "" or looks_encrypted(raw):
            continue
        cipher = kms.encrypt(raw.encode("utf-8"))
        bind.execute(
            text(f"UPDATE {table} SET {column} = :c WHERE id = :id"),
            {"c": cipher, "id": row[0]},
        )


def _decrypt(table: str, column: str, bind) -> None:
    kms = get_kms()
    rows = bind.execute(text(f"SELECT id, {column} FROM {table}")).fetchall()
    for row in rows:
        raw = row[1]
        if raw is None or not looks_encrypted(raw):
            continue
        plain = kms.decrypt(raw).decode("utf-8")
        bind.execute(
            text(f"UPDATE {table} SET {column} = :c WHERE id = :id"),
            {"c": plain, "id": row[0]},
        )


def upgrade() -> None:
    bind = op.get_bind()
    # 1) totp_secret: VARCHAR(64) -> TEXT
    op.alter_column(
        "plat_account",
        "totp_secret",
        type_=sa.Text(),
        existing_type=sa.String(64),
        postgresql_using="totp_secret::text",
    )
    _reencrypt("plat_account", "totp_secret", bind)

    # 2) health_tags: JSON -> TEXT（USING 转文本），再重加密
    op.alter_column(
        "mt_customer",
        "health_tags",
        type_=sa.Text(),
        existing_type=sa.JSON(),
        postgresql_using="health_tags::text",
    )
    _reencrypt("mt_customer", "health_tags", bind)


def downgrade() -> None:
    # 解密回明文（同 KMS 可逆）；开发态可用，生产不建议对加密数据 downgrade。
    bind = op.get_bind()
    _decrypt("plat_account", "totp_secret", bind)
    op.alter_column(
        "plat_account",
        "totp_secret",
        type_=sa.String(64),
        existing_type=sa.Text(),
        postgresql_using="totp_secret::text",
    )
    _decrypt("mt_customer", "health_tags", bind)
    op.alter_column(
        "mt_customer",
        "health_tags",
        type_=sa.JSON(),
        existing_type=sa.Text(),
        postgresql_using="health_tags::json",
    )
