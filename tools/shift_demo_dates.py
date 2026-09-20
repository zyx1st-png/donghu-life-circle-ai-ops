#!/usr/bin/env python3
"""把整套 Demo Seed 的日期平移到新的"演示当天"。

为什么需要它：seed 里所有日期都锚定在 2026-09-20。如果演示改期，
C003 会过 expire_at，推荐 Agent 会直接拒绝它，Before/After 这场核心戏就没了。
手工改 6 个 CSV 里的几十个时间戳既慢又容易改漏。

用法：
    python3 tools/shift_demo_dates.py --to 2026-10-11            # 预演，只打印
    python3 tools/shift_demo_dates.py --to 2026-10-11 --write    # 真正写入
    python3 tools/shift_demo_dates.py --to 2026-10-13 --exact --write

默认按整周平移（--to 会向前吸附到同一星期几），这样 seed 里
"本周六早市""周一早高峰"这类措辞不会和 event_time 的实际星期对不上。
--exact 允许任意天数，但平移后会逐条检查并报告星期措辞冲突。
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = os.path.join(ROOT, "demo", "seed-data")
ANCHOR_FILE = os.path.join(ROOT, "demo", "anchor.txt")
FILES = ["Residents", "Contents", "Interactions", "Needs", "Services", "Push_Plans"]

DATE_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
WEEKDAY_RE = re.compile(r"周([一二三四五六日天])")
CN_WEEKDAY = "一二三四五六日"


def read_anchor() -> dt.date:
    return dt.date.fromisoformat(open(ANCHOR_FILE, encoding="utf-8").read().strip())


def shift_text(text: str, delta: dt.timedelta) -> str:
    def repl(m):
        d = dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))) + delta
        return d.isoformat()
    return DATE_RE.sub(repl, text)


def check_weekdays(contents_text: str, plans_text: str) -> list[str]:
    """平移后，内容里的"周X"措辞是否仍与 event_time 的实际星期一致。"""
    import csv, io
    problems = []
    contents = {r["content_id"]: r for r in csv.DictReader(io.StringIO(contents_text))}
    for cid, row in contents.items():
        ev = (row.get("event_time") or "").strip()
        if not ev:
            continue
        actual = CN_WEEKDAY[dt.datetime.strptime(ev[:10], "%Y-%m-%d").weekday()]
        for fieldname in ("title", "summary"):
            for w in WEEKDAY_RE.findall(row.get(fieldname, "")):
                if w in ("日", "天"):
                    w = "日"
                if w != actual:
                    problems.append(
                        f"{cid}.{fieldname} 写的是「周{w}」，但 event_time {ev[:10]} 是周{actual}")
    for row in csv.DictReader(io.StringIO(plans_text)):
        cid = row["content_id"]
        ev = (contents.get(cid, {}).get("event_time") or "").strip()
        if not ev:
            continue
        actual = CN_WEEKDAY[dt.datetime.strptime(ev[:10], "%Y-%m-%d").weekday()]
        for w in WEEKDAY_RE.findall(row.get("message_text", "")):
            if w in ("日", "天"):
                w = "日"
            if w != actual:
                problems.append(
                    f"{row['push_id']}.message_text 写的是「周{w}」，但 {cid} 的 event_time "
                    f"{ev[:10]} 是周{actual}")
    return problems


def main():
    ap = argparse.ArgumentParser(description="平移 Demo Seed 的全部日期")
    ap.add_argument("--to", required=True, metavar="YYYY-MM-DD", help="新的演示当天")
    ap.add_argument("--exact", action="store_true",
                    help="按精确天数平移，不吸附到整周（星期措辞可能需要手工改）")
    ap.add_argument("--write", action="store_true", help="真正写入文件（默认只预演）")
    args = ap.parse_args()

    anchor = read_anchor()
    target = dt.date.fromisoformat(args.to)
    raw_days = (target - anchor).days
    if raw_days == 0:
        print(f"锚点已经是 {anchor}，无需平移。")
        return 0

    if args.exact:
        days = raw_days
    else:
        days = (raw_days // 7) * 7
        if days == 0:
            print(f"错误：{target} 与锚点 {anchor} 相差 {raw_days} 天，不足一周。\n"
                  f"      用 --exact 精确平移，或选择 {anchor + dt.timedelta(days=7)} "
                  f"之后的同一星期几。")
            return 1

    new_anchor = anchor + dt.timedelta(days=days)
    delta = dt.timedelta(days=days)
    gap = (target - new_anchor).days

    print(f"锚点 {anchor}（周{CN_WEEKDAY[anchor.weekday()]}）"
          f" → {new_anchor}（周{CN_WEEKDAY[new_anchor.weekday()]}），平移 {days} 天")
    if gap:
        print(f"注意：新锚点比 {target} 早 {gap} 天。彩排请跑 "
              f"`--today {target}`，确认没有内容提前过期。")

    texts = {}
    total = 0
    for name in FILES:
        path = os.path.join(SEED, f"{name}.csv")
        src = open(path, encoding="utf-8", newline="\n").read()
        dst = shift_text(src, delta)
        n = len(DATE_RE.findall(src))
        total += n
        texts[name] = (path, dst)
        print(f"  {name+'.csv':<20} {n} 个日期")

    for p in check_weekdays(texts["Contents"][1], texts["Push_Plans"][1]):
        print(f"  WARN 星期措辞冲突：{p}")

    if not args.write:
        print(f"\n预演完成，共 {total} 个日期。加 --write 真正写入。")
        return 0

    for path, dst in texts.values():
        open(path, "w", encoding="utf-8", newline="\n").write(dst)
    open(ANCHOR_FILE, "w", encoding="utf-8").write(f"{new_anchor}\n")
    print(f"\n已写入 {total} 个日期，锚点更新为 {new_anchor}。")
    print(f"下一步：python3 tools/validate_demo_data.py --today {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
