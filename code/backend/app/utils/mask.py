"""敏感字段脱敏工具（等保三级：审计留痕敏感字段落库前脱敏）。

提供 mask_json：递归遍历 dict/list，对命中敏感键名的值做掩码，
用于 write_audit 在落库前对 before/after_json 脱敏，保证明文不入审计表。
哈希链基于脱敏后的内容计算，verify_audit_chain 仍自洽。
"""
import re
from typing import Any

# 敏感键名（含中英文/常见变体），命中即脱敏
_SENSITIVE_KEYS = {
    "id_card", "idcard", "id_card_no", "id_number", "身份证", "证件号",
    "phone", "mobile", "phone_number", "tel", "手机号", "电话",
    "real_name", "name", "patient_name", "真实姓名", "姓名", "患者姓名",
    "email", "邮箱", "mail",
    "address", "地址", "住址",
    "bank_card", "bankcard", "银行卡",
}

# 身份证/手机号正则（用于值侧兜底命中，即使键未匹配）
_ID_CARD_RE = re.compile(r"^\d{15}$|^\d{17}[\dXx]$")
_PHONE_RE = re.compile(r"^1[3-9]\d{9}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def mask_id_card(v: str) -> str:
    """身份证：保留前 6 后 4，中间打码。"""
    if len(v) <= 10:
        return "*" * len(v)
    return v[:6] + "*" * (len(v) - 10) + v[-4:]


def mask_phone(v: str) -> str:
    """手机号：保留前 3 后 4。"""
    if len(v) <= 7:
        return "*" * len(v)
    return v[:3] + "*" * (len(v) - 7) + v[-4:]


def mask_name(v: str) -> str:
    """姓名：保留首字，其余打码。"""
    if len(v) <= 1:
        return v + "*"
    return v[0] + "*" * (len(v) - 1)


def mask_email(v: str) -> str:
    """邮箱：保留首字符与域名。"""
    if "@" not in v:
        return "*" * len(v)
    local, domain = v.split("@", 1)
    head = local[0] if local else "*"
    return f"{head}***@{domain}"


def mask_value(v: str) -> str:
    """按类型自动选择掩码策略（值侧兜底）。"""
    if _ID_CARD_RE.match(v):
        return mask_id_card(v)
    if _PHONE_RE.match(v):
        return mask_phone(v)
    if _EMAIL_RE.match(v):
        return mask_email(v)
    # 其它字符串：保留首字其余打码（避免明文暴露）
    if len(v) <= 1:
        return v + "*"
    return v[0] + "*" * (len(v) - 1)


def _is_sensitive_key(key: str) -> bool:
    return key.lower() in _SENSITIVE_KEYS


def mask_json(obj: Any) -> Any:
    """递归脱敏：dict 的敏感键 value、list 的元素均处理；非容器原样返回。

    返回新的脱敏副本，不修改入参。
    """
    if isinstance(obj, dict):
        out: dict = {}
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                out[k] = mask_json(v)
            elif isinstance(v, str) and (_is_sensitive_key(k) or _looks_sensitive(v)):
                out[k] = mask_value(v)
            else:
                out[k] = v
        return out
    if isinstance(obj, list):
        return [mask_json(item) for item in obj]
    return obj


def _looks_sensitive(v: str) -> bool:
    """值侧兜底：键未命中但值形如身份证/手机/邮箱。"""
    return bool(_ID_CARD_RE.match(v) or _PHONE_RE.match(v) or _EMAIL_RE.match(v))
