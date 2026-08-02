"""ih_doctor.dept_id -> ih_department 外键化（H6）

Revision ID: 0016
Revises: 0015
Create Date: 2026-08-02

将 IhDoctor.dept（科室名称字符串）平滑迁移为 dept_id 外键关联 ih_department：
1. 新增 nullable 列 dept_id（BIGINT）与索引；
2. 按 dept 名称回填 dept_id（未匹配置 NULL，不强制约束，避免丢失历史）；
3. 建立外键约束（引用 ih_department.id），保证引用完整性。
dept 字符串保留作为冗余过渡字段。

幂等：列已存在则跳过整段逻辑，可安全重跑。
"""

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None

_DOCTOR = "ih_doctor"
_DEPT = "ih_department"
_FK = "fk_ih_doctor_dept_id"


def _column_exists(bind, table: str, column: str) -> bool:
    return bool(
        bind.execute(
            sa.text(
                "select 1 from information_schema.columns "
                "where table_name=:t and column_name=:c"
            ),
            {"t": table, "c": column},
        ).first()
    )


def upgrade() -> None:
    bind = op.get_bind()
    if _column_exists(bind, _DOCTOR, "dept_id"):
        return

    # 1) 加列
    op.add_column(_DOCTOR, sa.Column("dept_id", sa.BigInteger(), nullable=True))
    op.create_index("ix_ih_doctor_dept_id", _DOCTOR, ["dept_id"])

    # 2) 按科室名称回填 dept_id（未匹配置 NULL）
    op.execute(
        sa.text(
            f"""
            UPDATE {_DOCTOR}
            SET dept_id = (
                SELECT d.id FROM {_DEPT} d
                WHERE d.name = {_DOCTOR}.dept
                  AND d.is_deleted IS NOT TRUE
                LIMIT 1
            )
            WHERE {_DOCTOR}.dept IS NOT NULL
              AND {_DOCTOR}.dept_id IS NULL
            """
        )
    )

    # 3) 外键约束（引用 ih_department.id）
    op.create_foreign_key(
        _FK,
        _DOCTOR,
        _DEPT,
        ["dept_id"],
        ["id"],
        ondelete="NO ACTION",
    )


def downgrade() -> None:
    bind = op.get_bind()
    if not _column_exists(bind, _DOCTOR, "dept_id"):
        return
    op.drop_constraint(_FK, _DOCTOR, type_="foreignkey")
    op.drop_index("ix_ih_doctor_dept_id", table_name=_DOCTOR)
    op.drop_column(_DOCTOR, "dept_id")
