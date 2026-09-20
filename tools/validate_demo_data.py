#!/usr/bin/env python3
"""校验东湖生活圈 MVP-0 Demo Seed 数据。

用法：
    python3 tools/validate_demo_data.py                      # 全量校验
    python3 tools/validate_demo_data.py --today 2026-09-20   # 指定"演示当天"
    python3 tools/validate_demo_data.py --explain C003       # 看某条内容的逐人推荐判定
    python3 tools/validate_demo_data.py --explain C003 --after-quick-capture

退出码：0 = 全部通过；1 = 有 ERROR。

为什么需要它：Demo 必须连续彩排 3 次结果一致。人工核对 25×15 的推荐矩阵不现实，
而且 seed 数据一旦被手改，Before/After 这类剧情不变量会无声失效。
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import re
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])

from donghu_demo import (  # noqa: E402
    ENUMS, MULTI_FIELDS, REGIONS, SCHEMA, Dataset,
    _split, evaluate, format_targets, parse_time, recommend,
)

ERRORS: list[str] = []
WARNINGS: list[str] = []


def err(msg): ERRORS.append(msg)
def warn(msg): WARNINGS.append(msg)


TABLES = [
    ("Residents", "residents", "resident_id"),
    ("Contents", "contents", "content_id"),
    ("Interactions", "interactions", "interaction_id"),
    ("Needs", "needs", "need_id"),
    ("Services", "services", "service_id"),
    ("Push_Plans", "push_plans", "push_id"),
]


def check_schema(ds: Dataset):
    for table, attr, _ in TABLES:
        rows = getattr(ds, attr)
        if not rows:
            err(f"[{table}] 空表")
            continue
        got, want = list(rows[0].keys()), SCHEMA[table]
        if got != want:
            missing, extra = set(want) - set(got), set(got) - set(want)
            if missing: err(f"[{table}] 缺少字段: {sorted(missing)}")
            if extra:   err(f"[{table}] 多出字段: {sorted(extra)}")
            if not missing and not extra:
                warn(f"[{table}] 字段顺序与 PRD 不一致")


def check_ids(ds: Dataset):
    for table, attr, key in TABLES:
        seen = set()
        prefix = {"Residents": "R", "Contents": "C", "Interactions": "I",
                  "Needs": "N", "Services": "S", "Push_Plans": "P"}[table]
        for row in getattr(ds, attr):
            v = row[key]
            if v in seen:
                err(f"[{table}] {key} 重复: {v}")
            seen.add(v)
            if not re.fullmatch(rf"{prefix}\d{{3}}", v):
                err(f"[{table}] {key} 不符合 {prefix}NNN 格式: {v}")


def check_required(ds: Dataset):
    required = {
        "Residents": ["resident_id", "display_name", "status"],
        "Contents": ["content_id", "title", "summary", "content_type",
                     "commercial_level", "risk_level", "status"],
        "Interactions": ["interaction_id", "resident_id", "interaction_time",
                         "interaction_type", "raw_note"],
        "Needs": ["need_id", "resident_id", "need_category", "need_summary", "status"],
        "Services": ["service_id", "provider_name", "service_name",
                     "service_category", "service_summary", "status"],
        "Push_Plans": ["push_id", "push_date", "content_id", "recommend_reason",
                       "message_text", "review_status", "send_status"],
    }
    for table, attr, key in TABLES:
        for row in getattr(ds, attr):
            for f in required[table]:
                if not (row.get(f) or "").strip():
                    err(f"[{table}] {row[key]} 必填字段为空: {f}")
    # active 内容必须有 expire_at：空值曾等同于"永不过期"，活动结束几周后仍会被推
    for c in ds.contents:
        if c["status"] == "active" and not (c["expire_at"] or "").strip():
            err(f"[Contents] {c['content_id']} status=active 但 expire_at 为空。"
                f"时效无法判定时应保留 status=draft")


def check_vocab(ds: Dataset):
    by_table = {t: attr for t, attr, _ in TABLES}
    for spec, allowed in ENUMS.items():
        table, fieldname = spec.split(".")
        keyfield = dict((t, k) for t, _, k in TABLES)[table]
        for row in getattr(ds, by_table[table]):
            v = (row.get(fieldname) or "").strip()
            if v not in allowed:
                err(f"[{table}] {row[keyfield]}.{fieldname} 值不在词表内: {v!r} "
                    f"(允许: {allowed})")
    for spec, allowed in MULTI_FIELDS.items():
        table, fieldname = spec.split(".")
        keyfield = dict((t, k) for t, _, k in TABLES)[table]
        for row in getattr(ds, by_table[table]):
            for v in _split(row.get(fieldname, "")):
                if v not in allowed:
                    err(f"[{table}] {row[keyfield]}.{fieldname} 含未冻结取值: {v!r}")

    for r in ds.residents:
        if r["community"] and r["community"] not in REGIONS:
            err(f"[Residents] {r['resident_id']}.community 未冻结取值: {r['community']!r}")
    for c in ds.contents:
        if c["region"] and c["region"] not in REGIONS:
            err(f"[Contents] {c['content_id']}.region 未冻结取值: {c['region']!r}")

    for c in ds.contents:
        tp = _split(c["target_population"])
        if "全部居民" in tp and len(tp) > 1:
            err(f"[Contents] {c['content_id']}.target_population 同时含 全部居民 和具体人群，语义矛盾: {tp}")


def check_refs(ds: Dataset):
    rids = {r["resident_id"] for r in ds.residents}
    cids = {c["content_id"] for c in ds.contents}
    sids = {s["service_id"] for s in ds.services}

    for i in ds.interactions:
        if i["resident_id"] not in rids:
            err(f"[Interactions] {i['interaction_id']} 引用了不存在的 resident_id: {i['resident_id']}")
        rt, rel = i["related_type"], (i["related_id"] or "").strip()
        if rel:
            pool = {"content": cids, "service": sids}.get(rt)
            if pool is not None and rel not in pool:
                err(f"[Interactions] {i['interaction_id']} 引用了不存在的 {rt}: {rel}")
        if rel and not rt:
            err(f"[Interactions] {i['interaction_id']} 有 related_id 但无 related_type")

    for n in ds.needs:
        if n["resident_id"] not in rids:
            err(f"[Needs] {n['need_id']} 引用了不存在的 resident_id: {n['resident_id']}")
        ms = (n["matched_service_id"] or "").strip()
        if ms and ms not in sids:
            err(f"[Needs] {n['need_id']} 引用了不存在的 service_id: {ms}")
        if n["status"] == "resolved" and not ms:
            err(f"[Needs] {n['need_id']} status=resolved 但没有 matched_service_id")
        if n["status"] == "unable_to_resolve" and ms:
            err(f"[Needs] {n['need_id']} status=unable_to_resolve 但填了 matched_service_id")

    for p in ds.push_plans:
        if p["content_id"] not in cids:
            err(f"[Push_Plans] {p['push_id']} 引用了不存在的 content_id: {p['content_id']}")
        for fieldname in ("target_residents", "no_send_residents"):
            for token in _split(p.get(fieldname, "")):
                rid = token.split()[0]
                if rid not in rids:
                    err(f"[Push_Plans] {p['push_id']}.{fieldname} 引用了不存在的居民: {token}")
                else:
                    want = next(r["display_name"] for r in ds.residents if r["resident_id"] == rid)
                    if token != f"{rid} {want}":
                        err(f"[Push_Plans] {p['push_id']}.{fieldname} 姓名与 Residents 不一致: "
                            f"{token!r} 应为 {rid + ' ' + want!r}")


def check_dates(ds: Dataset, today: dt.datetime):
    for c in ds.contents:
        pub, ev, exp = (parse_time(c[k]) for k in ("publish_time", "event_time", "expire_at"))
        if pub and ev and ev < pub:
            err(f"[Contents] {c['content_id']} event_time 早于 publish_time")
        if c["status"] == "active" and exp and exp < today:
            err(f"[Contents] {c['content_id']} status=active 但已过 expire_at "
                f"({c['expire_at']} < {today:%Y-%m-%d %H:%M})，"
                f"推荐 Agent 会拒绝它 —— 请先跑 tools/shift_demo_dates.py")
        if c["status"] == "expired" and exp and exp >= today:
            warn(f"[Contents] {c['content_id']} status=expired 但 expire_at 还没到")

    for r in ds.residents:
        li = parse_time(r["last_interaction_at"])
        actual = [parse_time(i["interaction_time"]) for i in ds.interactions_of(r["resident_id"])]
        actual = [t for t in actual if t]
        if actual:
            newest = max(actual)
            if li != newest:
                err(f"[Residents] {r['resident_id']}.last_interaction_at={r['last_interaction_at']} "
                    f"与 Interactions 最新记录 {newest:%Y-%m-%d %H:%M} 不一致")
        if li and li > today:
            err(f"[Residents] {r['resident_id']}.last_interaction_at 晚于演示当天")

    for i in ds.interactions:
        t = parse_time(i["interaction_time"])
        if t and t > today:
            err(f"[Interactions] {i['interaction_id']} 互动时间晚于演示当天")


def check_push_plans(ds: Dataset, today: dt.datetime):
    """核心检查：seed 里写死的推送计划，必须等于规则引擎算出来的结果。

    不一致 = 彩排时 Agent 的实时输出会和表里的 Before 状态对不上。
    """
    for p in ds.push_plans:
        result = recommend(ds, p["content_id"], today)
        if result["gate"]:
            err(f"[Push_Plans] {p['push_id']} 的内容 {p['content_id']} {result['gate']}")
            continue
        for col, bucket in (("target_residents", "send_today"),
                            ("no_send_residents", "no_send"),
                            ("hold_residents", "hold")):
            want = format_targets(result[bucket])
            if p.get(col, "") != want:
                err(f"[Push_Plans] {p['push_id']} ({p['content_id']}) {col} 与规则结果不一致\n"
                    f"    表内: {p.get(col, '')}\n"
                    f"    规则: {want}")
        # target_residents 是当天的执行名单，HOLD 的人绝不能出现在里面
        held = {d.resident_id for d in result["hold"]}
        for token in _split(p.get("target_residents", "")):
            if token.split()[0] in held:
                err(f"[Push_Plans] {p['push_id']} 的 target_residents 含今日 HOLD 居民: {token}")


def check_sheet_setup():
    """docs/sheet-setup.md 是 WorkBuddy 照着建表的依据，字段必须和 CSV 表头一致。

    这份文档一旦漂了，建出来的表和 seed CSV 对不上列，导入会静默错位。
    """
    import os
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "docs", "sheet-setup.md")
    if not os.path.exists(path):
        warn("docs/sheet-setup.md 不存在，跳过建表规格校验")
        return
    lines = open(path, encoding="utf-8").read().splitlines()
    current, fields, seen, done = None, [], {}, False
    for line in lines + ["## END"]:
        if line.startswith("## "):
            if current and fields:
                seen[current] = fields
            title = line[3:].strip()
            current = title.split(" ", 1)[1].replace(" ", "_") if " " in title else None
            fields, done = [], False
        elif current and not done and line.startswith("|"):
            cell = line.strip("|").split("|")[0].strip()
            if cell == "字段" or set(cell) <= set("-: "):
                continue
            fields.append(cell)
        elif current and fields and not line.startswith("|"):
            done = True   # 只取每节的第一张表（Needs 后面还有一张系统字段表）
    for table, want in SCHEMA.items():
        got = seen.get(table)
        if got is None:
            err(f"[sheet-setup.md] 缺少 {table} 的字段表")
        elif got != want:
            err(f"[sheet-setup.md] {table} 字段与 CSV 表头不一致\n"
                f"    文档: {got}\n    表头: {want}")


# ---------------------------------------------------------------- Demo 剧情不变量

def quick_capture_after(ds: Dataset, today: dt.datetime) -> Dataset:
    """模拟现场 Quick Capture：3栋张姐(R003) 询问小学生周末活动。"""
    after = copy.deepcopy(ds)
    r = after.resident("R003")
    r["recent_interests"] = "亲子活动"
    r["last_interaction_at"] = f"{today:%Y-%m-%d} 10:30"
    r["profile_summary"] = "关注社区活动；近期主动咨询适合小学生参加的周末活动。"
    after.interactions.append({
        "interaction_id": "I021", "resident_id": "R003",
        "interaction_time": f"{today:%Y-%m-%d} 10:30",
        "interaction_type": "activity_inquiry", "related_type": "content", "related_id": "C003",
        "raw_note": "3栋张姐问最近有没有适合小学生周末参加的活动。",
        "ai_summary": "张姐主动询问适合小学生参加的周末活动。",
        "topic_tags": "亲子活动", "sentiment": "neutral", "created_by": "operator",
    })
    return after


def check_demo_invariants(ds: Dataset, today: dt.datetime):
    """config/operating-rules.md 里承诺的剧情，必须真的成立。"""
    def ok(cond, label, detail=""):
        if not cond:
            err(f"[DEMO 不变量] {label} 失败{(' — ' + detail) if detail else ''}")

    # 1. C003 Before：张姐不在名单
    before = recommend(ds, "C003", today)
    ids = [d.resident_id for d in before["send_today"]]
    ok("R003" not in ids, "C003 Before 不应包含 R003 张姐", f"当前名单 {ids}")
    ok(len(ids) >= 3, "C003 Before 名单不应过小", f"当前 {len(ids)} 人")

    # 2. C003 After：张姐进入，且理由引用了刚才的互动
    after_ds = quick_capture_after(ds, today)
    after = recommend(after_ds, "C003", today)
    after_ids = [d.resident_id for d in after["send_today"]]
    ok("R003" in after_ids, "C003 After 应包含 R003 张姐", f"当前名单 {after_ids}")
    ok(set(after_ids) - set(ids) == {"R003"},
       "Before→After 只应新增 R003", f"差异 {set(after_ids) - set(ids)}")
    d3 = next((d for d in after["send_today"] if d.resident_id == "R003"), None)
    ok(d3 and ("E2" in d3.evidence or "E3" in d3.evidence),
       "R003 的 After 推荐理由必须来自近期互动而非长期兴趣",
       f"evidence={d3.evidence if d3 else None}")

    # 3. C005 促销：陈叔 NO_SEND
    c005 = recommend(ds, "C005", today)
    no_ids = [d.resident_id for d in c005["no_send"]]
    ok("R009" in no_ids, "C005 应对 R009 陈叔输出 NO_SEND", f"当前 NO_SEND {no_ids}")
    d9 = next((d for d in c005["no_send"] if d.resident_id == "R009"), None)
    ok(d9 and "avoid_topics" in d9.reason, "R009 的 NO_SEND 理由必须是 avoid_topics")

    # 4. 陈叔不是被整体屏蔽：非促销的东湖内容他照收
    c001 = recommend(ds, "C001", today)
    ok("R009" in [d.resident_id for d in c001["send_today"]],
       "R009 陈叔应仍然收到 C001 东湖早市（证明 NO_SEND 是按主题而非按人）")
    ok(not c001["hold"], "C001 不应有 HOLD 居民", f"当前 {[d.resident_id for d in c001['hold']]}")

    # 5. 王阿姨的上门助浴：服务库里确实没有供给
    bath = [s for s in ds.services
            if "助浴" in s["service_name"] + s["service_summary"]
            or "洗浴" in s["service_name"] + s["service_summary"]]
    ok(not bath, "Services 中不得存在上门助浴服务（否则 R014 Need 演示失效）",
       f"发现 {[s['service_id'] for s in bath]}")
    ok(ds.resident("R014") is not None and not _split(ds.resident("R014")["recent_needs"]),
       "R014 王阿姨初始不应带 recent_needs（现场才产生）")

    # 6. 重名消歧：张姐必须有两个，且 identify_note 不同
    zhang = [r for r in ds.residents if r["display_name"] == "张姐"]
    ok(len(zhang) == 2, "应保留两位张姐用于演示重名消歧", f"当前 {len(zhang)} 位")
    ok(len({r["identify_note"] for r in zhang}) == 2, "两位张姐的 identify_note 必须不同")

    # 7. HOLD 与执行名单：必须存在一个真实的 SEND+HOLD 场景，且它不进当天名单
    c011 = recommend(ds, "C011", today)
    held = [d.resident_id for d in c011["hold"]]
    ok("R018" in held,
       "C011 应把 R018 小刘判为 HOLD（内容适配，但今日不主动触达）", f"当前 HOLD {held}")
    ok("R018" not in [d.resident_id for d in c011["send_today"]],
       "HOLD 居民不得出现在当天执行名单 target_residents 里")
    ok("R018" in [d.resident_id for d in c011["eligible"]],
       "HOLD 不应丢失适配信息：R018 仍应属于 eligible")

    # 8. unable_to_resolve 的需求必须还能被未来的新供给重新匹配
    ok(any(n["need_id"] == "N004" for n in ds.unmet_needs_of("R022")),
       "unable_to_resolve 的 Need 应仍算未满足，否则未来引入服务时匹配不回原居民")
    probe = copy.deepcopy(ds)
    probe.contents.append({
        "content_id": "C900", "title": "（探针）上门老人理发", "source": "", "source_url": "",
        "summary": "新引入的上门理发服务。", "content_type": "老人服务",
        "topic_tags": "老人服务", "target_population": "老人家庭", "region": "东湖",
        "publish_time": f"{today:%Y-%m-%d %H:%M}", "event_time": "",
        "expire_at": f"{today + dt.timedelta(days=30):%Y-%m-%d %H:%M}",
        "commercial_level": "service", "risk_level": "low", "status": "active",
        "operator_note": "",
    })
    rematched = [d.resident_id for d in recommend(probe, "C900", today)["send_today"]]
    ok("R022" in rematched,
       "东湖引入新服务后，此前 unable_to_resolve 的居民应重新进入候选",
       f"当前候选 {rematched}")

    # 9. 至少要有一条已过期内容，用来演示时效判断
    ok([c for c in ds.contents if c["status"] == "expired"], "Demo 需要至少 1 条 expired 内容")

    # 10. 未满足需求必须存在，运营摘要才有招商线索可讲
    unmet = [n for n in ds.needs if n["status"] == "unable_to_resolve"]
    ok(len(unmet) >= 2, "Demo 需要至少 2 条 unable_to_resolve 的 Need", f"当前 {len(unmet)} 条")


# ---------------------------------------------------------------- explain

def explain(ds: Dataset, content_id: str, today: dt.datetime, after_qc: bool):
    if after_qc:
        ds = quick_capture_after(ds, today)
    result = recommend(ds, content_id, today)
    c = result["content"]
    print(f"\n{c['content_id']} {c['title']}")
    print(f"  topic_tags      : {c['topic_tags']}")
    print(f"  target_population: {c['target_population']}")
    print(f"  commercial_level: {c['commercial_level']}   status: {c['status']}   "
          f"expire_at: {c['expire_at']}")
    print(f"  演示当天        : {today:%Y-%m-%d %H:%M}"
          + ("   [已模拟 Quick Capture]" if after_qc else ""))
    if result["gate"]:
        print(f"\n  ⛔ {result['gate']}")
        return
    print(f"\n  当天执行名单 target_residents（{len(result['send_today'])} 人）")
    for d in result["send_today"]:
        print(f"    {d.resident_id} {d.display_name:<6} [{'+'.join(d.evidence)}]  {d.reason}")
    print(f"\n  今日不主动触达 HOLD（{len(result['hold'])} 人，内容适配但暂停）")
    for d in result["hold"]:
        print(f"    {d.resident_id} {d.display_name:<6} [{'+'.join(d.evidence)}]  {d.reason}")
    if not result["hold"]:
        print("    （无）")
    print(f"\n  NO_SEND（{len(result['no_send'])} 人）")
    for d in result["no_send"]:
        print(f"    {d.resident_id} {d.display_name:<6} {d.reason}")
    if not result["no_send"]:
        print("    （无：没有居民的明确禁忌与本内容冲突）")
    print(f"\n  不合格 {len(result['not_eligible'])} 人（无主题依据或人群不符，不算 NO_SEND）")
    if result["content"]["commercial_level"] == "service":
        print("\n  ⚠ 本条为服务类内容：以上是**候选集合**，不是最终答案。\n"
              "     Agent 还需对每位候选做能力级核对（类目相同 ≠ 能办同一件事）。")
    print(f"\n  target_residents  = {format_targets(result['send_today'])}")
    print(f"  no_send_residents = {format_targets(result['no_send'])}")
    print(f"  hold_residents    = {format_targets(result['hold'])}")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="校验东湖生活圈 MVP-0 Demo Seed 数据")
    ap.add_argument("--today", default=None,
                    help="演示当天日期 YYYY-MM-DD（默认读 demo/anchor.txt）")
    ap.add_argument("--explain", metavar="CONTENT_ID", help="打印某条内容的逐人推荐判定")
    ap.add_argument("--after-quick-capture", action="store_true",
                    help="与 --explain 合用：模拟张姐 Quick Capture 之后的状态")
    args = ap.parse_args()

    anchor_file = __file__.rsplit("/", 2)[0] + "/demo/anchor.txt"
    today_str = args.today or open(anchor_file, encoding="utf-8").read().strip()
    today = dt.datetime.strptime(today_str, "%Y-%m-%d").replace(hour=12)
    ds = Dataset.load()

    if args.explain:
        explain(ds, args.explain, today, args.after_quick_capture)
        return 0

    check_schema(ds)
    if ERRORS:   # 字段对不上时后面的检查都没意义
        _report()
        return 1

    check_ids(ds)
    check_required(ds)
    check_vocab(ds)
    check_refs(ds)
    check_dates(ds, today)
    check_push_plans(ds, today)
    check_sheet_setup()
    check_demo_invariants(ds, today)

    print(f"演示当天: {today:%Y-%m-%d}")
    print(f"数据量  : 居民 {len(ds.residents)} / 内容 {len(ds.contents)} / 互动 "
          f"{len(ds.interactions)} / 需求 {len(ds.needs)} / 服务 {len(ds.services)} / "
          f"推送 {len(ds.push_plans)}")
    return _report()


def _report():
    for w in WARNINGS:
        print(f"WARN  {w}")
    for e in ERRORS:
        print(f"ERROR {e}")
    print()
    if ERRORS:
        print(f"✗ {len(ERRORS)} 个错误，{len(WARNINGS)} 个警告")
        return 1
    print(f"✓ 全部通过（{len(WARNINGS)} 个警告）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
