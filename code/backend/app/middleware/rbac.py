"""RBAC 角色与模块映射（技术架构第10.2章六角色）。

细粒度权限由 app.core.deps.require_role 依赖控制；此处提供模块级粗粒度映射骨架，
供路径级拦截或网关配置参考。
"""
# 六角色
ROLES = {"patient", "doctor", "store", "therapist", "platform", "xingyao"}

# 模块前缀 -> 允许角色（粗粒度占位）
ROLE_MODULE_MAP = {
    "ih": {"patient", "doctor", "platform"},
    "mt": {"store", "therapist", "platform"},
    "plat": {"platform", "xingyao"},
}


def module_of(path: str) -> str | None:
    """从 /api/v1/{ih|mt|plat}/... 提取模块名。"""
    parts = path.split("/")
    if len(parts) >= 4 and parts[1] == "api" and parts[2] == "v1":
        return parts[3]
    return None
