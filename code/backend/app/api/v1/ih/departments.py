"""互联网医院：科室结构管理（PRD 3.3 医院管理）。

- 列表只读、带分页/关键字筛选。
- 写操作（增改删）由 platform 角色执行。
"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import actor_of, get_db, require_role
from app.core.errors import BusinessError, ErrorCode
from app.core.response import success
from app.models.ih_models import IhDepartment
from app.schemas.common import PageResult
from app.schemas.ih import DepartmentCreate, DepartmentOut, DepartmentUpdate
from app.services.audit import write_audit

router = APIRouter(prefix="/departments", tags=["ih-科室结构"])


@router.get("", response_model=None)
async def list_departments(
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    conds = [IhDepartment.is_deleted.is_(False)]
    if keyword:
        conds.append(or_(IhDepartment.name.ilike(f"%{keyword}%"), IhDepartment.head.ilike(f"%{keyword}%")))
    total = (await db.execute(select(func.count()).select_from(IhDepartment).where(*conds))).scalar() or 0
    rows = (
        await db.execute(
            select(IhDepartment).where(*conds).order_by(IhDepartment.id.desc()).limit(page_size).offset((page - 1) * page_size)
        )
    ).scalars().all()
    return success(
        data=PageResult[DepartmentOut](
            total=total, page=page, page_size=page_size, items=[DepartmentOut.model_validate(r) for r in rows]
        )
    )


@router.get("/{department_id}", response_model=None)
async def get_department(department_id: int, db: AsyncSession = Depends(get_db)):
    d = await db.get(IhDepartment, department_id)
    if not d or d.is_deleted:
        raise BusinessError(ErrorCode.NOT_FOUND, "科室不存在")
    return success(data=DepartmentOut.model_validate(d))


@router.post("", response_model=None)
async def create_department(
    body: DepartmentCreate,
    request: Request,
    user: dict = Depends(require_role("platform")),
    db: AsyncSession = Depends(get_db),
):
    d = IhDepartment(**body.model_dump())
    db.add(d)
    await db.commit()
    await db.refresh(d)
    await write_audit(
        db,
        action="department.create",
        resource="ih_department",
        role=user.get("role"),
        actor_id=actor_of(user),
        after=DepartmentOut.model_validate(d).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    return success(data=DepartmentOut.model_validate(d))


@router.patch("/{department_id}", response_model=None)
async def update_department(
    department_id: int,
    body: DepartmentUpdate,
    request: Request,
    user: dict = Depends(require_role("platform")),
    db: AsyncSession = Depends(get_db),
):
    d = await db.get(IhDepartment, department_id)
    if not d or d.is_deleted:
        raise BusinessError(ErrorCode.NOT_FOUND, "科室不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(d, k, v)
    await db.commit()
    await db.refresh(d)
    await write_audit(
        db,
        action="department.update",
        resource="ih_department",
        role=user.get("role"),
        actor_id=actor_of(user),
        after=DepartmentOut.model_validate(d).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    return success(data=DepartmentOut.model_validate(d))


@router.delete("/{department_id}", response_model=None)
async def delete_department(
    department_id: int,
    request: Request,
    user: dict = Depends(require_role("platform")),
    db: AsyncSession = Depends(get_db),
):
    d = await db.get(IhDepartment, department_id)
    if not d or d.is_deleted:
        raise BusinessError(ErrorCode.NOT_FOUND, "科室不存在")
    d.is_deleted = True
    await db.commit()
    await write_audit(
        db,
        action="department.delete",
        resource="ih_department",
        role=user.get("role"),
        actor_id=actor_of(user),
        ip=request.client.host if request.client else None,
    )
    return success(message="已删除")
