"""业务单据号生成（技术架构第11章）。"""
from datetime import datetime


def gen_no(prefix: str) -> str:
    """生成前缀 + 时间戳(微秒) 的唯一单据号。"""
    return f"{prefix}{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
