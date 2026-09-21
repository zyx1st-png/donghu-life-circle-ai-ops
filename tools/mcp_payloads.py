#!/usr/bin/env python3
"""把 Demo Seed 转成腾讯文档智能表格 MCP 可直接调用的 payload，并做写后核对。

为什么需要它（全部来自 T0 实测，不是推断）：

- **B6**：半角 `;` 在任何路径都不会被拆成多选值。CSV 直导生成的是在线表格而不是
  智能表格，单元格原样保留整串 `买菜生鲜;社区活动`；把整串写进多选字段则会生成
  一个名叫「买菜生鲜;社区活动」的选项。所以 seed 必须在仓库侧拆成数组再写。
- **B3**：写入词表外的值会**静默新建选项**，还会把原有多选值整体替换。不报错。
  所以必须在生成 payload 之前就用真实的选项集合做 fail-closed 校验——
  未知值一律拒绝生成，而不是写进去之后再补救。
- **B5**：dateTime 用东八区毫秒时间戳。转换集中在 donghu_demo.py 里做一次。
- **A2**：`add_records` 用错误格式调用会返回 success 但写入空记录。
  所以每次关键写入之后必须 `list_records` 读回核对，本工具的 verify 负责这一步。

本工具**不连接 MCP**，只产出 JSON 和核对结论。实际调用由 WorkBuddy 执行。

用法：
    python3 tools/mcp_payloads.py fields                      # 建表 payload
    python3 tools/mcp_payloads.py records --table Residents   # 写记录 payload（需 --options）
    python3 tools/mcp_payloads.py check-options               # 词表漂移体检
    python3 tools/mcp_payloads.py verify --table Residents --dump d.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from donghu_demo import (  # noqa: E402
    DATETIME, FIELD_KINDS, SCHEMA, SELECT, SINGLE, Dataset,
    _split, field_options, from_cst_millis, to_cst_millis,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OPTIONS = os.path.join(ROOT, "demo", "smartsheet-options.json")

# T0 A2 实测：field_values 的形状是 [{field, text_value | option_value | string_value}]，
# 其中 field 用**字段标题**匹配（C2）。文本用 text_value、多选用 option_value 已实测确认。
# A2 恰好测了三种字段类型（单行文本 / 多选 / 日期时间），也恰好记录了三个取值键，
# 因此这三者都有实测支撑。**只有 singleSelect 没被测到**，它需要 Build 第 0 步确认。
VALUE_KEY = {
    "text": "text_value",          # T0 A2 实测确认
    SELECT: "option_value",        # T0 A2 实测确认（items 数组）
    SINGLE: "option_value",        # 待确认：未被 T0 覆盖，按与多选同族推定
    DATETIME: "string_value",      # T0 A2 + B5 实测确认（东八区毫秒时间戳，读回逐字一致）
}

DATE_ONLY = {("Push_Plans", "push_date")}   # PRD 里是「日期」而非「日期时间」


# ---------------------------------------------------------------- 选项快照

def load_options(path: str) -> dict:
    """读取 WorkBuddy 建完表后 list_fields 的选项快照。

    容忍两种形态：
      1. 归一形式  {"Residents": {"family_stage": {"亲子家庭": "optX", ...}}}
      2. list_fields 原始结构（尽量从常见键名里找 options）
    解析不出来时明确报错，绝不猜。
    """
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)

    def options_of(field_obj) -> dict[str, str] | None:
        if isinstance(field_obj, dict) and all(isinstance(v, str) for v in field_obj.values()):
            return dict(field_obj)                      # 已是 {text: option_id}
        for key in ("property_select", "select", "property"):
            prop = field_obj.get(key) if isinstance(field_obj, dict) else None
            if isinstance(prop, dict) and isinstance(prop.get("options"), list):
                out = {}
                for o in prop["options"]:
                    text = o.get("text") or o.get("name") or o.get("value")
                    if text is None:
                        raise ValueError(f"选项缺少 text/name/value：{o}")
                    out[text] = o.get("id") or o.get("option_id") or ""
                return out
        return None

    parsed: dict[str, dict[str, dict[str, str]]] = {}
    for table, payload in raw.items():
        fields = payload.get("fields", payload) if isinstance(payload, dict) else payload
        table_map: dict[str, dict[str, str]] = {}
        if isinstance(fields, dict):
            for fname, fobj in fields.items():
                opts = options_of(fobj)
                if opts is not None:
                    table_map[fname] = opts
        elif isinstance(fields, list):
            for fobj in fields:
                fname = fobj.get("field_title") or fobj.get("title") or fobj.get("name")
                if fname is None:
                    raise ValueError(f"字段缺少 field_title/title/name：{fobj}")
                opts = options_of(fobj)
                if opts is not None:
                    table_map[fname] = opts
        else:
            raise ValueError(f"{table} 的结构无法解析：期望 dict 或 list")
        parsed[table] = table_map
    return parsed


# ---------------------------------------------------------------- 建表 payload

def build_fields(table: str) -> dict:
    fields = []
    for name in SCHEMA[table]:
        kind = FIELD_KINDS[table][name]
        spec: dict = {"field_title": name, "field_type": kind}
        opts = field_options(table, name)
        if opts is not None:
            spec["property_select"] = {"options": [{"text": o} for o in opts]}
        fields.append(spec)
    return {"table": table, "fields": fields}


# ---------------------------------------------------------------- 记录 payload

def build_records(ds: Dataset, table: str, options: dict) -> tuple[list, list[str]]:
    attr = {"Residents": "residents", "Contents": "contents", "Interactions": "interactions",
            "Needs": "needs", "Services": "services", "Push_Plans": "push_plans"}[table]
    known = options.get(table, {})
    problems, records = [], []

    for name in SCHEMA[table]:
        if FIELD_KINDS[table][name] in (SELECT, SINGLE) and name not in known:
            problems.append(f"{table}.{name} 在选项快照里不存在——建表时漏了这个字段，或快照过期")

    for row in getattr(ds, attr):
        rid = row[SCHEMA[table][0]]
        values = []
        for name in SCHEMA[table]:
            raw = (row.get(name) or "").strip()
            if not raw:
                continue
            kind = FIELD_KINDS[table][name]
            if kind == DATETIME:
                ms = to_cst_millis(raw)
                values.append({"field": name, VALUE_KEY[DATETIME]: str(ms)})
            elif kind in (SELECT, SINGLE):
                items = sorted(_split(raw)) if kind == SELECT else [raw]
                for it in items:
                    if it not in known.get(name, {}):
                        problems.append(
                            f"{table}.{rid}.{name} 的取值「{it}」不在该字段已注册的选项里。"
                            f"直接写会静默新建选项（T0 B3），已拒绝生成。")
                values.append({"field": name, VALUE_KEY[kind]: {"items": items}})
            else:
                values.append({"field": name, VALUE_KEY["text"]: raw})
        records.append({"field_values": values})
    return records, problems


# ---------------------------------------------------------------- 词表漂移体检

def check_options(options: dict) -> list[str]:
    """把线上真实选项集合和仓库冻结词表逐字段比对。

    T0 B3 保证了漂移一定是无声的，所以这一步必须在每轮彩排前跑。
    """
    findings = []
    for table, cols in FIELD_KINDS.items():
        live_table = options.get(table)
        if live_table is None:
            findings.append(f"[缺失] 快照里没有 {table}")
            continue
        for name, kind in cols.items():
            if kind not in (SELECT, SINGLE):
                continue
            want = set(field_options(table, name) or [])
            live = set((live_table.get(name) or {}).keys())
            if live_table.get(name) is None:
                findings.append(f"[缺失] {table}.{name} 在快照里没有选项")
                continue
            for extra in sorted(live - want):
                findings.append(f"[漂移] {table}.{name} 线上多出未冻结选项「{extra}」")
            for missing in sorted(want - live):
                findings.append(f"[缺项] {table}.{name} 线上缺少选项「{missing}」")
    return findings


# ---------------------------------------------------------------- 写后读回核对

def verify(ds: Dataset, table: str, dump_path: str) -> list[str]:
    """把 list_records 的读回结果和 seed 逐字段比对。

    T0 A2：add_records 格式错误时返回 success 但写入空记录。
    所以"调用成功"和"真的写进去了"必须分开确认，这里做后者。

    重复业务 ID 也算失败。add_records 在结果不确定时重试（超时、网络抖动）
    会造成非幂等的重复写入，而两条内容完全相同的记录逐字段比对是全绿的——
    只有按主键计数才看得出来。
    """
    attr = {"Residents": "residents", "Contents": "contents", "Interactions": "interactions",
            "Needs": "needs", "Services": "services", "Push_Plans": "push_plans"}[table]
    key = SCHEMA[table][0]
    expected = {r[key]: r for r in getattr(ds, attr)}

    with open(dump_path, encoding="utf-8") as fh:
        raw = json.load(fh)
    rows = raw.get("records", raw) if isinstance(raw, dict) else raw

    findings, counts = [], {}
    for rec in rows:
        fv = rec.get("field_values", rec)
        got = {}
        if isinstance(fv, list):
            for item in fv:
                name = item.get("field") or item.get("field_title")
                got[name] = _read_value(item)
        else:
            got = {k: _read_value(v) if isinstance(v, dict) else v for k, v in fv.items()}

        rid = got.get(key)
        rid = rid[0] if isinstance(rid, list) and rid else rid
        if not rid or isinstance(rid, list):
            findings.append(f"[空记录] 读回一条没有 {key} 的记录——典型的静默写入失败（T0 A2）")
            continue
        counts[rid] = counts.get(rid, 0) + 1
        if rid not in expected:
            if counts[rid] == 1:
                findings.append(f"[多余] 线上存在 seed 里没有的 {rid}")
            continue
        if counts[rid] > 1:
            continue        # 内容比对只做第一条，重复单独报
        for name in SCHEMA[table]:
            want = (expected[rid].get(name) or "").strip()
            raw_have = got.get(name)
            kind = FIELD_KINDS[table][name]
            if kind in (SELECT, SINGLE):
                # 选项逐个比，绝不先拼成字符串再拆——那样
                # 「一个名叫『买菜生鲜;社区活动』的选项」会被还原成两个选项，
                # 而这恰好是 T0 B6 的失败形态，必须能看出来。
                have_items = sorted(raw_have if isinstance(raw_have, list)
                                    else ([] if not raw_have else [str(raw_have).strip()]))
                want_items = sorted(_split(want)) if kind == SELECT else ([want] if want else [])
                if have_items != want_items:
                    findings.append(f"[不符] {rid}.{name} 期望 {want_items}，读回 {have_items}")
                continue
            have = "" if raw_have is None else str(raw_have).strip()
            if kind == DATETIME and have:
                have = from_cst_millis(have, date_only=(table, name) in DATE_ONLY)
            if want != have:
                findings.append(f"[不符] {rid}.{name} 期望 {want!r}，读回 {have!r}")
    for rid, n in sorted(counts.items()):
        if n > 1:
            findings.append(f"[重复] {rid} 在线上出现 {n} 条——"
                            f"写入重试造成的非幂等重复，两条内容相同时逐字段比对看不出来")
    for rid in sorted(set(expected) - set(counts)):
        findings.append(f"[缺失] {rid} 没有写进去")
    return findings


def _read_value(item):
    if not isinstance(item, dict):
        return item
    for k in ("text_value", "string_value", "number_value"):
        if k in item and item[k] not in (None, ""):
            return item[k]
    ov = item.get("option_value")
    items = ov.get("items") if isinstance(ov, dict) else (ov if isinstance(ov, list) else None)
    if isinstance(items, list):
        # 返回列表而不是拼接字符串：选项之间的边界是判断
        # 「两个选项」还是「一个带分号的选项」的唯一依据，不能丢。
        return [str(i.get("text", i)) if isinstance(i, dict) else str(i) for i in items]
    return item.get("value", "")


# ---------------------------------------------------------------- CLI

def main():
    ap = argparse.ArgumentParser(description="SmartSheet MCP payload 生成与写后核对")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pf = sub.add_parser("fields", help="生成 add_fields payload")
    pf.add_argument("--table", help="只生成某张表")
    pf.add_argument("--out", help="写入文件而不是打印")

    pr = sub.add_parser("records", help="生成 add_records payload（未知选项值会拒绝生成）")
    pr.add_argument("--table", required=True)
    pr.add_argument("--options", default=DEFAULT_OPTIONS)
    pr.add_argument("--out")

    pc = sub.add_parser("check-options", help="线上选项集合 vs 冻结词表")
    pc.add_argument("--options", default=DEFAULT_OPTIONS)

    pv = sub.add_parser("verify", help="list_records 读回结果 vs seed")
    pv.add_argument("--table", required=True)
    pv.add_argument("--dump", required=True)

    a = ap.parse_args()
    ds = Dataset.load()

    if a.cmd == "fields":
        tables = [a.table] if a.table else list(SCHEMA)
        payload = [build_fields(t) for t in tables]
        return _emit(payload, a.out, f"{sum(len(p['fields']) for p in payload)} 个字段，{len(tables)} 张表")

    if a.cmd == "records":
        if not os.path.exists(a.options):
            print(f"✗ 找不到选项快照：{a.options}\n"
                  f"  这是 fail-closed 设计：没有线上真实选项集合就不生成 payload，\n"
                  f"  否则未注册的取值会被静默新建成选项（T0 B3）。\n"
                  f"  请先建表，再用 list_fields 导出快照，格式见 docs/mcp-write-contract.md。")
            return 1
        records, problems = build_records(ds, a.table, load_options(a.options))
        if problems:
            print(f"✗ 拒绝生成 {a.table} 的 payload，{len(problems)} 个问题：")
            for p in problems:
                print(f"  {p}")
            return 1
        return _emit({"table": a.table, "records": records}, a.out, f"{len(records)} 条记录")

    if a.cmd == "check-options":
        if not os.path.exists(a.options):
            print(f"✗ 找不到选项快照：{a.options}")
            return 1
        findings = check_options(load_options(a.options))
        for f in findings:
            print(f)
        print(f"\n{'✗ ' + str(len(findings)) + ' 处不一致' if findings else '✓ 线上选项与冻结词表完全一致'}")
        return 1 if findings else 0

    if a.cmd == "verify":
        findings = verify(ds, a.table, a.dump)
        for f in findings:
            print(f)
        print(f"\n{'✗ ' + str(len(findings)) + ' 处不符' if findings else '✓ ' + a.table + ' 读回结果与 seed 完全一致'}")
        return 1 if findings else 0


def _emit(payload, out, summary):
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"✓ 已写入 {out}（{summary}）")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
