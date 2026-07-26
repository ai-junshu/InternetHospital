# 导入各分域模型，确保 Alembic 迁移时 Base.metadata 已注册全部表
from app.models import ih_models, mt_models, plat_models  # noqa: F401
