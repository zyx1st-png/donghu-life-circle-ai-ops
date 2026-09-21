#!/usr/bin/env python3
"""mcp_payloads 的回归测试。

跑法：python3 tools/test_mcp_payloads.py

覆盖的都是 T0 实测出来的真实失败模式，不是假想场景：
分号不拆、词表静默漂移、写入静默失败、时区算错。
每一条都先构造出失败，再确认工具能抓到。
"""

from __future__ import annotations

import copy
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from donghu_demo import (FIELD_KINDS, SCHEMA, SELECT, SINGLE, Dataset, field_options,
                          to_cst_millis)
from mcp_payloads import (build_fields, build_records, check_options, field_census,
                          load_options, verify)

PASSED, FAILED = [], []


def case(name):
    def deco(fn):
        try:
            fn()
            PASSED.append(name)
        except AssertionError as e:
            FAILED.append(f"{name}: {e}")
        except Exception as e:                                  # noqa: BLE001
            FAILED.append(f"{name}: 意外异常 {type(e).__name__}: {e}")
        return fn
    return deco


def make_snapshot() -> dict:
    """模拟建完表后 list_fields 的原始返回。"""
    snap = {}
    for table, cols in FIELD_KINDS.items():
        fields = []
        for i, (name, kind) in enumerate(cols.items()):
            f = {"field_id": f"fld{i:03d}", "field_title": name, "field_type": kind}
            if kind in (SELECT, SINGLE):
                # 与真实 list_fields 返回一致：singleSelect 的选项在
                # property_single_select 里（Build Phase 1 实测 22020）。
                prop = "property_single_select" if kind == SINGLE else "property_select"
                f[prop] = {"options": [
                    {"id": f"opt{j:03d}", "text": o}
                    for j, o in enumerate(field_options(table, name))]}
            fields.append(f)
        snap[table] = {"fields": fields}
    return snap


def as_dump(records: list) -> dict:
    """把 add_records payload 翻成 list_records 读回的形状。"""
    out = []
    for r in records:
        fv = []
        for v in r["field_values"]:
            if "option_value" in v:
                fv.append({"field": v["field"], "option_value": {
                    "items": [{"id": f"opt{i}", "text": o["text"]}
                              for i, o in enumerate(v["option_value"]["items"])]}})
            elif "text_value" in v:
                fv.append({"field": v["field"], "text_value": {
                    "items": [dict(t) for t in v["text_value"]["items"]]}})
            else:
                fv.append(dict(v))
        out.append({"record_id": f"rec{len(out)}", "field_values": fv})
    return {"records": out}


def write_tmp(obj) -> str:
    fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(obj, fh, ensure_ascii=False)
    fh.close()
    return fh.name


DS = Dataset.load()
SNAP_RAW = make_snapshot()
SNAP_PATH = write_tmp(SNAP_RAW)
SNAP = load_options(SNAP_PATH)


@case("建表 payload 为每个选项字段预设了完整词表")
def _():
    for table in FIELD_KINDS:
        for f in build_fields(table)["fields"]:
            kind = FIELD_KINDS[table][f["field_title"]]
            if kind in (SELECT, SINGLE):
                prop = "property_single_select" if kind == SINGLE else "property_select"
                got = [o["text"] for o in f[prop]["options"]]
                want = field_options(table, f["field_title"])
                assert got == want, f"{table}.{f['field_title']} 选项不一致"
            else:
                assert "property_select" not in f and "property_single_select" not in f, \
                    f"{table}.{f['field_title']} 不该有选项"


@case("多选值被拆成 items 数组，而不是留成带分号的整串（T0 B6）")
def _():
    recs, problems = build_records(DS, "Residents", SNAP)
    assert not problems, problems
    rid_of = lambda r: next(v["text_value"]["items"][0]["text"]
                            for v in r["field_values"] if v["field"] == "resident_id")
    r003 = next(r for r in recs if rid_of(r) == "R003")
    r004 = next(r for r in recs if rid_of(r) == "R004")
    lti = next(v for v in r004["field_values"] if v["field"] == "long_term_interests")
    assert [o["text"] for o in lti["option_value"]["items"]] == ["买菜生鲜", "社区活动"], lti
    for v in r003["field_values"] + r004["field_values"]:
        for item in v.get("option_value", {}).get("items", []):
            assert ";" not in item["text"] and "；" not in item["text"], \
                f"选项里混进了分号: {item}"


@case("dateTime 写成东八区毫秒时间戳，且与 T0 B5 实测值一致")
def _():
    recs, _ = build_records(DS, "Contents", SNAP)
    c003 = next(r for r in recs
                if any(v.get("text_value", {}).get("items", [{}])[0].get("text") == "C003"
                       for v in r["field_values"]))
    ev = next(v for v in c003["field_values"] if v["field"] == "event_time")
    assert ev["string_value"] == "1790386200000", ev      # C003 event_time = 2026-09-26 09:30
    assert to_cst_millis("2026-09-26 09:30") == 1790386200000


@case("线上缺选项时拒绝生成 payload，而不是写进去再补救（T0 B3）")
def _():
    broken = copy.deepcopy(SNAP)
    del broken["Residents"]["long_term_interests"]["买菜生鲜"]
    recs, problems = build_records(DS, "Residents", broken)
    assert problems, "缺选项却照样生成了 payload"
    assert any("买菜生鲜" in p and "R004" in p for p in problems), problems


@case("选项字段在快照里整个缺失时也要拒绝")
def _():
    broken = copy.deepcopy(SNAP)
    del broken["Residents"]["avoid_topics"]
    _, problems = build_records(DS, "Residents", broken)
    assert any("avoid_topics" in p for p in problems), problems


@case("check-options 抓得到 Agent 静默新建的选项")
def _():
    drifted = copy.deepcopy(SNAP)
    drifted["Residents"]["recent_interests"]["儿童活动"] = "optDRIFT"
    findings = check_options(drifted)
    assert any("儿童活动" in f and "漂移" in f for f in findings), findings


@case("check-options 抓得到建表时漏建的选项")
def _():
    missing = copy.deepcopy(SNAP)
    del missing["Contents"]["risk_level"]["high"]
    findings = check_options(missing)
    assert any("risk_level" in f and "缺少" in f for f in findings), findings


@case("check-options 对干净快照零告警")
def _():
    assert check_options(SNAP) == [], check_options(SNAP)


@case("verify 对正确读回零告警")
def _():
    recs, _ = build_records(DS, "Needs", SNAP)
    assert verify(DS, "Needs", write_tmp(as_dump(recs))) == []


@case("verify 抓得到静默写出的空记录（T0 A2）")
def _():
    recs, _ = build_records(DS, "Needs", SNAP)
    bad = copy.deepcopy(recs)
    bad[2]["field_values"] = []
    findings = verify(DS, "Needs", write_tmp(as_dump(bad)))
    assert any("空记录" in f for f in findings), findings


@case("verify 抓得到漏写的记录")
def _():
    recs, _ = build_records(DS, "Needs", SNAP)
    dump = as_dump(recs)
    dump["records"].pop()
    findings = verify(DS, "Needs", write_tmp(dump))
    assert any("[缺失]" in f for f in findings), findings


@case("verify 抓得到 8 小时时区偏差")
def _():
    recs, _ = build_records(DS, "Needs", SNAP)
    dump = as_dump(recs)
    for v in dump["records"][0]["field_values"]:
        if v["field"] == "created_at":
            v["string_value"] = str(int(v["string_value"]) + 8 * 3600 * 1000)
    findings = verify(DS, "Needs", write_tmp(dump))
    assert any("created_at" in f and "不符" in f for f in findings), findings


@case("verify 抓得到多选字段被写成一个带分号的选项（T0 B6 的失败形态）")
def _():
    recs, _ = build_records(DS, "Residents", SNAP)
    dump = as_dump(recs)
    for rec in dump["records"]:
        for v in rec["field_values"]:
            if v["field"] == "long_term_interests" and len(v["option_value"]["items"]) > 1:
                texts = [i["text"] for i in v["option_value"]["items"]]
                v["option_value"]["items"] = [{"id": "optBAD", "text": ";".join(texts)}]
                break
    findings = verify(DS, "Residents", write_tmp(dump))
    assert any("long_term_interests" in f for f in findings), \
        "多选被合成一个带分号的选项，verify 没抓到"


@case("verify 抓得到重复写入（两条完全相同的正确记录）")
def _():
    recs, _ = build_records(DS, "Needs", SNAP)
    dump = as_dump(recs)
    dump["records"].append(copy.deepcopy(dump["records"][1]))   # 原样复制一条正确记录
    findings = verify(DS, "Needs", write_tmp(dump))
    assert any("[重复]" in f and "N002" in f for f in findings), findings
    assert not any("[不符]" in f for f in findings), \
        f"重复记录内容正确，不该报不符: {findings}"


@case("六张表都按各自主键检测重复")
def _():
    for table, dup_key in (("Residents", "R001"), ("Contents", "C001"),
                           ("Interactions", "I001"), ("Needs", "N001"),
                           ("Services", "S001"), ("Push_Plans", "P001")):
        recs, problems = build_records(DS, table, SNAP)
        assert not problems, (table, problems)
        dump = as_dump(recs)
        dump["records"].append(copy.deepcopy(dump["records"][0]))
        findings = verify(DS, table, write_tmp(dump))
        assert any("[重复]" in f and dup_key in f for f in findings), (table, findings)


@case("verify 抓得到多写的记录")
def _():
    recs, _ = build_records(DS, "Needs", SNAP)
    dump = as_dump(recs)
    dump["records"].append({"record_id": "recX", "field_values": [
        {"field": "need_id", "text_value": {"items": [{"text": "N099", "type": "text"}]}}]})
    findings = verify(DS, "Needs", write_tmp(dump))
    assert any("[多余]" in f and "N099" in f for f in findings), findings


@case("建字段：singleSelect 用 property_single_select，select 用 property_select")
def _():
    # Build Phase 1 实测：用错属性键会被整批拒绝（22020），同批其它字段也不会创建
    for table in FIELD_KINDS:
        for f in build_fields(table)["fields"]:
            kind = FIELD_KINDS[table][f["field_title"]]
            if kind == SINGLE:
                assert "property_single_select" in f, f"{table}.{f['field_title']} 单选用错属性键"
                assert "property_select" not in f
            elif kind == SELECT:
                assert "property_select" in f, f"{table}.{f['field_title']} 多选用错属性键"
                assert "property_single_select" not in f


@case("建字段：dateTime 必须带 property_date_time")
def _():
    # Build Phase 1 实测：不带会被拒（22018）
    from donghu_demo import DATETIME
    for table in FIELD_KINDS:
        for f in build_fields(table)["fields"]:
            if FIELD_KINDS[table][f["field_title"]] == DATETIME:
                assert "property_date_time" in f, f"{table}.{f['field_title']} 缺 property_date_time"
                assert f["property_date_time"].get("format"), "format 不能为空"


@case("写记录：text_value 和 option_value.items 都是对象数组，不是纯字符串")
def _():
    # Build Phase 1 实测：纯字符串连 MCP 参数校验都过不了
    recs, _ = build_records(DS, "Residents", SNAP)
    for v in recs[0]["field_values"]:
        if "text_value" in v:
            items = v["text_value"]["items"]
            assert all(i.get("type") == "text" and "text" in i for i in items), v
        if "option_value" in v:
            items = v["option_value"]["items"]
            assert all(isinstance(i, dict) and "text" in i for i in items), v
        if "string_value" in v:
            assert isinstance(v["string_value"], str) and v["string_value"].isdigit(), v


@case("字段普查区分业务字段与平台自带字段")
def _():
    census = {t: (biz, phys, plat) for t, biz, phys, plat in field_census(SNAP_PATH)}
    for table, cols in SCHEMA.items():
        biz, phys, plat = census[table]
        assert biz == len(cols), f"{table} 业务字段数应为 {len(cols)}"
        assert phys == biz, f"{table} 模拟快照不含平台字段，物理数应等于业务数"
    # 模拟真实 SmartSheet 的平台默认列
    raw = copy.deepcopy(SNAP_RAW)
    raw["Residents"]["fields"].append({"field_id": "fldSYS", "field_title": "智能表列",
                                       "field_type": "text"})
    biz, phys, plat = next((b, p, pl) for t, b, p, pl in field_census(write_tmp(raw))
                           if t == "Residents")
    assert (biz, phys, plat) == (13, 14, ["智能表列"]), (biz, phys, plat)


@case("选项快照的两种形态都能解析")
def _():
    normalized = {t: {f: dict(o) for f, o in cols.items()} for t, cols in SNAP.items()}
    assert load_options(write_tmp(normalized)) == SNAP


@case("无法解析的快照要明确报错，不能静默当成空")
def _():
    try:
        load_options(write_tmp({"Residents": {"fields": [{"no_title_key": 1}]}}))
    except ValueError as e:
        assert "field_title" in str(e), e
    else:
        raise AssertionError("结构不对却没有报错")


def main():
    for name in PASSED:
        print(f"  ✓ {name}")
    for f in FAILED:
        print(f"  ✗ {f}")
    print(f"\n{len(PASSED)} 通过，{len(FAILED)} 失败")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
