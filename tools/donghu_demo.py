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

# PRD v0.4.1 冻结字段顺序。
# Needs.created_at / updated_at 原计划用 SmartSheet 系统字段（PRD §29），
# 但 T0 C3 实测 createdTime / modifiedTime 的值 list_records 读不回，
# 因此改为普通 dateTime 字段并进入 CSV。
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
              "matched_service_id", "followup_note", "created_at", "updated_at"],
    "Services": ["service_id", "provider_name", "service_name", "service_category",
                 "service_summary", "price_description", "service_region", "target_population",
                 "contact", "status", "operator_note"],
    "Push_Plans": ["push_id", "push_date", "content_id", "target_residents", "target_segment",
                   "recommend_reason", "message_text", "no_send_residents", "no_send_reason",
                   "hold_residents", "hold_reason", "review_status", "send_status",
                   "operator_note"],
}

# ---------------------------------------------------------------- 规则参数

RECENT_INTERACTION_DAYS = 14   # E3：多久之内的互动算"近期"
NEGATIVE_HOLD_DAYS = 7         # HOLD：负反馈后多久不主动触达


def age_in_days(today: dt.datetime, t: dt.datetime | None) -> int | None:
    """记录距演示当天有多少天。未来时间返回负数，调用方必须拒绝。

    用日期粒度而不是时刻粒度：同一天的互动一律算 age=0，
    否则"上午 11 点录的互动"和"中午 12 点的基准时刻"之间几小时的差
    会让判定随运行时刻漂移。
    """
    if t is None:
        return None
    return (today.date() - t.date()).days


def is_recent(today: dt.datetime, t: dt.datetime | None, window: int) -> bool:
    """0 <= age <= window。未来时间不算近期——否则一条误填成明天的记录
    会被当成"刚刚发生"，而且永远不会过期。"""
    age = age_in_days(today, t)
    return age is not None and 0 <= age <= window

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

    def unmet_needs_of(self, rid):
        """尚未被满足的 Need。

        注意 unable_to_resolve 也算未满足：它表示"当前没有供给"，不是"这件事不用办了"。
        把它排除出匹配，会切断 未满足需求 → 服务引入/招商 → 重新连接居民
        这条商业闭环——王阿姨的助浴需求在东湖引入助浴服务后反而匹配不上她本人。
        只有 resolved 才是真正关闭。
        """
        return [n for n in self.needs
                if n["resident_id"] == rid
                and n["status"] in ("new", "following", "unable_to_resolve")]


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
                if is_recent(today, t, NEGATIVE_HOLD_DAYS):
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
    # E0 排在最前，因为 Needs 才是"具体待解决事项"的权威来源。
    # recent_needs / recent_interests 是为了看着方便而派生出来的画像字段，
    # 会被运营在画像整理时清空。如果只认派生字段，一条还躺在 Needs 表里
    # 的真实未满足需求，就会因为画像被清理而永远匹配不回本人。
    evidence, notes = [], []
    need_hits = [n for n in ds.unmet_needs_of(rid) if n["need_category"] in tags]
    if need_hits:
        evidence.append("E0")
        notes.append("未满足需求：" + "；".join(
            f"{n['need_id']} {n['need_summary']}" for n in need_hits))
    if _split(resident["recent_needs"]) & tags:
        evidence.append("E1")
        notes.append(f"近期需求命中 {'、'.join(sorted(_split(resident['recent_needs']) & tags))}")
    if _split(resident["recent_interests"]) & tags:
        evidence.append("E2")
        notes.append(f"近期关注 {'、'.join(sorted(_split(resident['recent_interests']) & tags))}")
    for i in ds.interactions_of(rid):
        t = parse_time(i["interaction_time"])
        if is_recent(today, t, RECENT_INTERACTION_DAYS) and (_split(i["topic_tags"]) & tags):
            if i["interaction_type"] != "negative_feedback":
                evidence.append("E3")
                notes.append(f"{t:%m-%d} 互动：{i['ai_summary'] or i['raw_note']}")
                break
    if _split(resident["long_term_interests"]) & tags:
        evidence.append("E4")
        notes.append(f"长期关注 {'、'.join(sorted(_split(resident['long_term_interests']) & tags))}")

    if not evidence:
        return out("NOT_ELIGIBLE", "无任何主题依据", hold=hold)

    # E0 与 E1/E2/E3 同属"明确且当前有效"的证据，可以越过人群门槛。
    # 一个人有没有待办的具体需求，比他属于哪个家庭阶段更有说服力。
    recent_evidence = bool({"E0", "E1", "E2", "E3"} & set(evidence))

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

    # --- 服务类内容：必须由 Need 本身触发，光有兴趣不够 ---
    if content["commercial_level"] == "service" and "E0" not in evidence:
        return out("NOT_ELIGIBLE", "服务类内容需要未满足的同类 Need 才主动推荐", evidence, hold=hold)

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
        if exp is None:
            # 空 expire_at 曾经等同于"永不过期"，是最危险的静默失效：
            # 活动结束几周后仍在推。判不了时效就应该留在 draft。
            gate = "内容 status=active 但 expire_at 为空，不参与推荐（时效无法判定时应保留 draft）"
        elif exp <= today:
            # 用 <= ：expire_at 是"到这一刻为止仍可发"的边界，到点即失效。
            gate = f"内容已过 expire_at（{c['expire_at']}），不参与推荐"

    decisions = [evaluate(ds, c, r, today) for r in ds.residents]
    eligible = [] if gate else [d for d in decisions if d.outcome == "SEND"]
    return {
        "content": c,
        "gate": gate,
        # 三层语义，见 config/recommendation-rules.md：
        #   eligible   = 内容与居民适配
        #   hold       = 适配，但今日不应主动触达
        #   send_today = eligible - hold  ← Push Plan.target_residents 只能由它生成
        "eligible": eligible,
        "send_today": [d for d in eligible if not d.hold],
        "hold": [d for d in eligible if d.hold],
        "no_send": [] if gate else [d for d in decisions if d.outcome == "NO_SEND"],
        "not_eligible": [d for d in decisions if d.outcome == "NOT_ELIGIBLE"],
    }


def format_targets(decisions: list[Decision]) -> str:
    """Push Plans.target_residents 的可读格式：R003 张姐；R011 小王"""
    return "；".join(f"{d.resident_id} {d.display_name}" for d in decisions)


# ---------------------------------------------------------------- SmartSheet 字段类型
#
# 只使用 T0 B1 实测确认可创建的类型。多行文本和 URL 一律按 text 建：
# MVP-0 不需要它们的 UI 特性，少一种类型就少一处未经验证的假设。

TEXT, SELECT, SINGLE, DATETIME = "text", "select", "singleSelect", "dateTime"

FIELD_KINDS = {
    "Residents": {
        "resident_id": TEXT, "display_name": TEXT, "identify_note": TEXT,
        "community": SINGLE, "family_stage": SELECT, "long_term_interests": SELECT,
        "recent_interests": SELECT, "recent_needs": SELECT, "avoid_topics": SELECT,
        "last_interaction_at": DATETIME, "profile_summary": TEXT,
        "operator_note": TEXT, "status": SINGLE,
    },
    "Contents": {
        "content_id": TEXT, "title": TEXT, "source": TEXT, "source_url": TEXT,
        "summary": TEXT, "content_type": SINGLE, "topic_tags": SELECT,
        "target_population": SELECT, "region": SINGLE, "publish_time": DATETIME,
        "event_time": DATETIME, "expire_at": DATETIME, "commercial_level": SINGLE,
        "risk_level": SINGLE, "status": SINGLE, "operator_note": TEXT,
    },
    "Interactions": {
        "interaction_id": TEXT, "resident_id": TEXT, "interaction_time": DATETIME,
        "interaction_type": SINGLE, "related_type": SINGLE, "related_id": TEXT,
        "raw_note": TEXT, "ai_summary": TEXT, "topic_tags": SELECT,
        "sentiment": SINGLE, "created_by": TEXT,
    },
    "Needs": {
        "need_id": TEXT, "resident_id": TEXT, "need_category": SINGLE,
        "need_summary": TEXT, "urgency": SINGLE, "status": SINGLE,
        "matched_service_id": TEXT, "followup_note": TEXT,
        "created_at": DATETIME, "updated_at": DATETIME,
    },
    "Services": {
        "service_id": TEXT, "provider_name": TEXT, "service_name": TEXT,
        "service_category": SINGLE, "service_summary": TEXT, "price_description": TEXT,
        "service_region": SELECT, "target_population": SELECT, "contact": TEXT,
        "status": SINGLE, "operator_note": TEXT,
    },
    "Push_Plans": {
        "push_id": TEXT, "push_date": DATETIME, "content_id": TEXT,
        "target_residents": TEXT, "target_segment": TEXT, "recommend_reason": TEXT,
        "message_text": TEXT, "no_send_residents": TEXT, "no_send_reason": TEXT,
        "hold_residents": TEXT, "hold_reason": TEXT, "review_status": SINGLE,
        "send_status": SINGLE, "operator_note": TEXT,
    },
}


def field_options(table: str, field: str) -> list[str] | None:
    """该字段应该预设哪些选项。text / dateTime 返回 None。"""
    kind = FIELD_KINDS[table][field]
    if kind not in (SELECT, SINGLE):
        return None
    spec = f"{table}.{field}"
    if spec in MULTI_FIELDS:
        return list(MULTI_FIELDS[spec])
    if spec in ENUMS:
        return [v for v in ENUMS[spec] if v]     # 去掉代表"留空"的空串
    if field in ("community", "region"):
        return list(REGIONS)
    raise KeyError(f"{spec} 是选项字段但没有冻结词表")


# ---------------------------------------------------------------- 时间转换
#
# T0 B5：腾讯文档智能表格的 dateTime 读写用东八区毫秒时间戳，API 层无时区偏移。
# 转换只在这里做一次。Prompt 不要各自实现，散落三份必然漂。
#
# 校准证据：T0 B5 写入 "2026-09-26 09:30" 得到 1790386200000，与本函数一致。

CST = dt.timezone(dt.timedelta(hours=8))


def to_cst_millis(value: str) -> int | None:
    """"YYYY-MM-DD HH:MM" 或 "YYYY-MM-DD" → 东八区毫秒时间戳。"""
    t = parse_time(value)
    if t is None:
        return None
    return int(t.replace(tzinfo=CST).timestamp() * 1000)


def from_cst_millis(ms: int | str, date_only: bool = False) -> str:
    """东八区毫秒时间戳 → "YYYY-MM-DD HH:MM"，用于读回核对。"""
    t = dt.datetime.fromtimestamp(int(ms) / 1000, CST)
    return f"{t:%Y-%m-%d}" if date_only else f"{t:%Y-%m-%d %H:%M}"
