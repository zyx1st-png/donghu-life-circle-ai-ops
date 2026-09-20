"""东湖生活圈 MVP-0 Demo 数据模型与推荐规则引擎。

本模块是 `config/recommendation-rules.md` 的可执行副本。
两者必须保持一致：改规则 → 同时改这里 → 跑 validate_demo_data.py。

MVP-0 用途只有两个：
1. 校验 demo seed 数据自洽；
2. 生成"预期推荐结果"，供彩排时和 Agent 实际输出对照。

它不是线上运行时。真正的推荐由 WorkBuddy 里的 Recommendation Agent 完成。
"""

from __future__ import annotations

import csv
import datetime as dt
import os
import re
from dataclasses import dataclass, field

SEED_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo", "seed-data")

# ---------------------------------------------------------------- 冻结词表

TOPIC_TAGS = [
    "亲子活动", "老人服务", "买菜生鲜", "餐饮美食", "家政服务", "维修服务",
    "社区活动", "健康活动", "教育学习", "文化娱乐", "运动健身", "交通出行",
    "天气提醒", "公共服务", "便民信息", "优惠促销", "其他",
]

FAMILY_STAGES = ["亲子家庭", "老人家庭", "年轻上班族", "普通家庭"]
TARGET_POPULATIONS = FAMILY_STAGES + ["全部居民"]
REGIONS = ["东湖", "东湖A区", "东湖B区", "东湖周边"]

ENUMS = {
    "Residents.status": ["active", "low_active", "dormant", "lost"],
    "Contents.status": ["draft", "active", "expired", "rejected"],
    "Contents.commercial_level": ["non_commercial", "weak_commercial", "service", "promotion"],
    "Contents.risk_level": ["low", "medium", "high"],
    "Contents.content_type": TOPIC_TAGS,
    "Interactions.interaction_type": [
        "content_reply", "active_inquiry", "service_inquiry", "service_request",
        "activity_inquiry", "activity_signup", "positive_feedback",
        "negative_feedback", "manual_followup", "other",
    ],
    "Interactions.related_type": ["content", "service", "need", "activity", ""],
    "Interactions.sentiment": ["positive", "neutral", "negative", ""],
    "Needs.need_category": TOPIC_TAGS,
    "Needs.urgency": ["normal", "high", ""],
    "Needs.status": ["new", "following", "resolved", "unable_to_resolve"],
    "Services.service_category": TOPIC_TAGS,
    "Services.status": ["active", "paused", "unverified"],
    "Push_Plans.review_status": ["draft", "approved", "rejected"],
    "Push_Plans.send_status": ["not_sent", "sent", "cancelled"],
}

# 多值字段（分隔符 ";"）及其允许词表
MULTI_FIELDS = {
    "Residents.family_stage": FAMILY_STAGES,
    "Residents.long_term_interests": TOPIC_TAGS,
    "Residents.recent_interests": TOPIC_TAGS,
    "Residents.recent_needs": TOPIC_TAGS,
    "Residents.avoid_topics": TOPIC_TAGS,
    "Contents.topic_tags": TOPIC_TAGS,
    "Contents.target_population": TARGET_POPULATIONS,
    "Interactions.topic_tags": TOPIC_TAGS,
    "Services.service_region": REGIONS,
    "Services.target_population": TARGET_POPULATIONS,
}

# PRD v0.4.1 冻结字段顺序（Needs 的 created_at / updated_at 使用 SmartSheet 系统字段，
# 不进 CSV —— 见 PRD §29）
SCHEMA = {
    "Residents": ["resident_id", "display_name", "identify_note", "community", "family_stage",
                  "long_term_interests", "recent_interests", "recent_needs", "avoid_topics",
                  "last_interaction_at", "profile_summary", "operator_note", "status"],
    "Contents": ["content_id", "title", "source", "source_url", "summary", "content_type",
                 "topic_tags", "target_population", "region", "publish_time", "event_time",
                 "expire_at", "commercial_level", "risk_level", "status", "operator_note"],
    "Interactions": ["interaction_id", "resident_id", "interaction_time", "interaction_type",
                     "related_type", "related_id", "raw_note", "ai_summary", "topic_tags",
                     "sentiment", "created_by"],
    "Needs": ["need_id", "resident_id", "need_category", "need_summary", "urgency", "status",
              "matched_service_id", "followup_note"],
    "Services": ["service_id", "provider_name", "service_name", "service_category",
                 "service_summary", "price_description", "service_region", "target_population",
                 "contact", "status", "operator_note"],
    "Push_Plans": ["push_id", "push_date", "content_id", "target_residents", "target_segment",
                   "recommend_reason", "message_text", "no_send_residents", "no_send_reason",
                   "review_status", "send_status", "operator_note"],
}

# ---------------------------------------------------------------- 规则参数

RECENT_INTERACTION_DAYS = 14   # E3：多久之内的互动算"近期"
NEGATIVE_HOLD_DAYS = 7         # HOLD：负反馈后多久不主动触达

# ---------------------------------------------------------------- 载入

def _split(v: str) -> set[str]:
    """多值字段拆分。同时接受半角 ; 和全角 ；—— 人工在 SmartSheet 里手打时两种都会出现。"""
    return {p.strip() for p in re.split(r"[;；]", v or "") if p.strip()}


def parse_time(v: str):
    v = (v or "").strip()
    if not v:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(v, fmt)
        except ValueError:
            continue
    raise ValueError(f"无法解析时间: {v!r}")


def load_table(name: str, seed_dir: str = SEED_DIR) -> list[dict]:
    path = os.path.join(seed_dir, f"{name}.csv")
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


@dataclass
class Dataset:
    residents: list[dict] = field(default_factory=list)
    contents: list[dict] = field(default_factory=list)
    interactions: list[dict] = field(default_factory=list)
    needs: list[dict] = field(default_factory=list)
    services: list[dict] = field(default_factory=list)
    push_plans: list[dict] = field(default_factory=list)

    @classmethod
    def load(cls, seed_dir: str = SEED_DIR) -> "Dataset":
        return cls(
            residents=load_table("Residents", seed_dir),
            contents=load_table("Contents", seed_dir),
            interactions=load_table("Interactions", seed_dir),
            needs=load_table("Needs", seed_dir),
            services=load_table("Services", seed_dir),
            push_plans=load_table("Push_Plans", seed_dir),
        )

    def resident(self, rid): return next((r for r in self.residents if r["resident_id"] == rid), None)
    def content(self, cid): return next((c for c in self.contents if c["content_id"] == cid), None)

    def interactions_of(self, rid):
        return [i for i in self.interactions if i["resident_id"] == rid]

    def open_needs_of(self, rid):
        return [n for n in self.needs
                if n["resident_id"] == rid and n["status"] in ("new", "following")]


# ---------------------------------------------------------------- 规则引擎

@dataclass
class Decision:
    resident_id: str
    display_name: str
    outcome: str          # SEND / NO_SEND / NOT_ELIGIBLE
    hold: bool            # 今日是否不主动触达（与 outcome 正交）
    evidence: list[str]   # 命中的证据编号 E1..E4
    reason: str           # 面向运营的中文理由


def evaluate(ds: Dataset, content: dict, resident: dict, today: dt.datetime) -> Decision:
    """对单个 (content, resident) 应用 config/recommendation-rules.md 的规则。"""
    rid, name = resident["resident_id"], resident["display_name"]
    tags = _split(content["topic_tags"])

    def out(outcome, reason, evidence=(), hold=False):
        return Decision(rid, name, outcome, hold, list(evidence), reason)

    # HOLD：整体减少打扰（与 SEND/NO_SEND 正交，单独标记）。
    # 只有"运营已把 status 调成 low_active" + "近期确有负反馈"两条同时成立才算，
    # 避免把"别发我促销"这种针对单一主题的反馈误读成"别联系我"——后者由 avoid_topics 处理。
    hold = False
    hold_note = ""
    if resident["status"] == "low_active":
        for i in ds.interactions_of(rid):
            if i["interaction_type"] == "negative_feedback":
                t = parse_time(i["interaction_time"])
                if t and (today - t).days <= NEGATIVE_HOLD_DAYS:
                    hold, hold_note = True, f"{t:%Y-%m-%d} 明确反馈消息过多，今日整体不主动触达"
                    break

    # --- 硬排除（N 系列）---
    avoid_hit = _split(resident["avoid_topics"]) & tags
    if avoid_hit:
        r = f"命中 avoid_topics：{'、'.join(sorted(avoid_hit))}"
        if hold:
            r += f"；且{hold_note}"
        return out("NO_SEND", r, hold=hold)

    if resident["status"] == "lost":
        return out("NO_SEND", "居民状态为 lost", hold=hold)

    # 已报名本条活动 → 不重复推送（这是"少发错"的一部分，不是"没依据"）
    for i in ds.interactions_of(rid):
        if (i["interaction_type"] == "activity_signup"
                and i["related_type"] == "content"
                and i["related_id"] == content["content_id"]):
            return out("NO_SEND", "已报名本条活动，不重复推送", hold=hold)

    # --- 证据（E 系列）---
    evidence, notes = [], []
    if _split(resident["recent_needs"]) & tags:
        evidence.append("E1")
        notes.append(f"近期需求命中 {'、'.join(sorted(_split(resident['recent_needs']) & tags))}")
    if _split(resident["recent_interests"]) & tags:
        evidence.append("E2")
        notes.append(f"近期关注 {'、'.join(sorted(_split(resident['recent_interests']) & tags))}")
    for i in ds.interactions_of(rid):
        t = parse_time(i["interaction_time"])
        if t and (today - t).days <= RECENT_INTERACTION_DAYS and (_split(i["topic_tags"]) & tags):
            if i["interaction_type"] != "negative_feedback":
                evidence.append("E3")
                notes.append(f"{t:%m-%d} 互动：{i['ai_summary'] or i['raw_note']}")
                break
    if _split(resident["long_term_interests"]) & tags:
        evidence.append("E4")
        notes.append(f"长期关注 {'、'.join(sorted(_split(resident['long_term_interests']) & tags))}")

    if not evidence:
        return out("NOT_ELIGIBLE", "无任何主题依据", hold=hold)

    recent_evidence = bool({"E1", "E2", "E3"} & set(evidence))

    # --- 人群门槛 ---
    tp = _split(content["target_population"])
    if tp and "全部居民" not in tp:
        if not (_split(resident["family_stage"]) & tp) and not recent_evidence:
            return out("NOT_ELIGIBLE",
                       f"人群不匹配（内容面向 {'、'.join(sorted(tp))}），且只有长期兴趣依据",
                       evidence, hold=hold)

    # --- 促销收紧：promotion 必须有近期依据 ---
    if content["commercial_level"] == "promotion" and not recent_evidence:
        return out("NOT_ELIGIBLE", "促销类内容要求近期依据，仅有长期兴趣不足", evidence, hold=hold)

    # --- 服务类内容：必须有未关闭的同类 Need ---
    if content["commercial_level"] == "service":
        if not any(n["need_category"] in tags for n in ds.open_needs_of(rid)):
            return out("NOT_ELIGIBLE", "服务类内容需要未关闭的同类 Need 才主动推荐", evidence, hold=hold)

    return out("SEND", "；".join(notes), evidence, hold=hold)


def recommend(ds: Dataset, content_id: str, today: dt.datetime) -> dict:
    """对一条内容跑完整推荐，返回 SEND / NO_SEND / HOLD / 不合格 的分组。"""
    c = ds.content(content_id)
    if c is None:
        raise KeyError(content_id)

    gate = None
    if c["status"] != "active":
        gate = f"内容 status={c['status']}，不参与推荐"
    else:
        exp = parse_time(c["expire_at"])
        if exp and exp < today:
            gate = f"内容已过 expire_at（{c['expire_at']}），不参与推荐"

    decisions = [evaluate(ds, c, r, today) for r in ds.residents]
    return {
        "content": c,
        "gate": gate,
        "send": [] if gate else [d for d in decisions if d.outcome == "SEND"],
        "no_send": [] if gate else [d for d in decisions if d.outcome == "NO_SEND"],
        "not_eligible": [d for d in decisions if d.outcome == "NOT_ELIGIBLE"],
    }


def format_targets(decisions: list[Decision]) -> str:
    """Push Plans.target_residents 的可读格式：R003 张姐；R011 小王"""
    return "；".join(f"{d.resident_id} {d.display_name}" for d in decisions)
