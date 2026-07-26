"""轻量 RAG 检索器（技术架构第10.3章：RAG 可解释输出）。

开发态采用内置「疼痛管理/调理」知识语料做关键词检索（标签重叠打分），
为方案推荐提供可解释依据，避免写死占位文案。

后续可无缝替换为 pgvector 向量检索：仅需替换 retrieve() 内部的向量化与
相似度计算，调用方（plan_recommend）无需改动。
"""
from typing import List

# 内置知识语料：标签命中即视为相关。可持续扩充或从 PG mt_knowledge 加载。
_KNOWLEDGE: List[dict] = [
    {"id": "K01", "tags": ["颈肩", "颈椎", "僵硬", "酸痛", "低头"],
     "text": "颈肩酸痛：建议热敷、低强度肩颈运动、姿势矫正，避免长期低头。"},
    {"id": "K02", "tags": ["腰椎", "腰突", "坐骨", "下背", "久坐"],
     "text": "腰椎问题：建议理疗、核心肌群训练、避免久坐与负重。"},
    {"id": "K03", "tags": ["膝", "关节", "关节炎", "上下楼", "软骨"],
     "text": "膝关节炎：建议低冲击运动（游泳/骑车）、体重管理、必要时理疗。"},
    {"id": "K04", "tags": ["慢性", "慢病", "长期", "并发症", "共病"],
     "text": "慢性/多慢病人群：建议定期复查、医生随访、个体化干预。"},
    {"id": "K05", "tags": ["剧烈", "高分", "急性", "重度"],
     "text": "疼痛评分偏高：建议强化调理（专业康复/药物辅助）并密切随访。"},
    {"id": "K06", "tags": ["睡眠", "作息", "疲劳", "亚健康", "焦虑"],
     "text": "亚健康/睡眠作息不佳：建议作息调整、放松训练、健康宣教。"},
    {"id": "K07", "tags": ["膳食", "饮食", "肥胖", "代谢", "营养"],
     "text": "代谢/膳食相关：建议膳食干预、营养评估、体重管理。"},
    {"id": "K08", "tags": ["老年", "高龄", "骨松", "骨质疏松", "跌倒"],
     "text": "高龄/骨质疏松风险：建议防跌倒、温和负重训练、骨密度监测。"},
]


def build_query(pain_type: str | None, pain_score: float, chronic_count: int, age: int) -> str:
    """将结构化特征翻译为检索语料可命中的查询串。"""
    parts = [pain_type or "", f"疼痛{pain_score}"]
    if chronic_count and chronic_count > 0:
        parts.append("慢性共病")
    if pain_score and pain_score >= 7:
        parts.append("剧烈高分")
    if age and age >= 60:
        parts.append("老年骨松")
    if age and age < 18:
        parts.append("青少年")
    return " ".join(p for p in parts if p)


def retrieve(query: str, top_k: int = 3) -> List[dict]:
    """关键词重叠检索，返回 top-k 知识条目（含 id/text）。"""
    q = (query or "").lower()
    scored = []
    for item in _KNOWLEDGE:
        score = sum(1 for tag in item["tags"] if tag.lower() in q)
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [it for _, it in scored[:top_k]]


def build_rationale(features: dict, plan: dict, hits: List[dict]) -> str:
    """组合 RAG 可解释依据（纯函数，便于单测，杜绝占位文案）。

    features: {version, age, pain_score, chronic_count, pain_type}
    plan: {plan_id, title, ...}
    hits: retrieve() 命中的知识条目
    """
    refs = "；".join(f"[{h['id']}] {h['text']}" for h in hits)
    return (
        f"模型(版本 {features.get('version')})依据特征"
        f"[年龄={features.get('age')}, 疼痛评分={features.get('pain_score')}, "
        f"慢病数={features.get('chronic_count')}, "
        f"疼痛类型={features.get('pain_type') or '未指定'}] "
        f"推荐方案「{plan.get('title')}」({plan.get('plan_id')})。"
        f"可解释依据(检索自知识库, top-{len(hits)}): "
        f"{refs or '无强匹配知识条目, 采用通用调理原则'}。"
        f"AI 仅供参考, 不替代医师诊断。"
    )
