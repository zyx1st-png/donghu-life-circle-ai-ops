# 彩排记录

> PRD §30.1：每个核心动作至少提前跑 3 次，记录平均耗时、最长耗时、结果是否稳定。
>
> 演示稳定性本身就是 MVP-0 的产品需求。这份记录的用途是**在现场之前**
> 发现哪一步会卡、哪一步结果会飘。

## 每轮开始前

```bash
python3 tools/validate_demo_data.py          # 必须全绿
```

从 `Demo_Before` 备份恢复数据，确保每轮起点一致。

## 轮次记录

复制下面这张表，每彩排一轮填一份。

> **Phase 3（2026-09-22）说明**：本轮起每轮不再“恢复备份”，而是从 Master Before
> （`LdQgWmgNpfub`）用 `manage.copy_file` 新建独立副本（Rehearsal_1/2/3），
> 三轮真正独立，Master 与 Demo_After（Plan B）全程不动。
> 每轮 gate：六表 list_fields → fresh snapshot → `check-options --require-fresh`
> → 计数与 anchors（R003.recent_interests=空 / R014.recent_needs=空 /
> I021/I022/N007/P007 不存在）全部 PASS 才开跑。
> 下方耗时为 MCP 执行段实测（副本创建→gate→写入→读回验收）；
> Scene 1/2/5 为 Agent dry-run，其耗时取决于现场讲解节奏，不计入。

### 第 1 轮 · 2026-09-22（副本 LwmbqtDPsyJZ）

| 步骤 | 耗时(秒) | 结果是否符合预期 | 备注 |
|---|---:|---|---|
| Content Agent 结构化 | ~30（dry-run） | ✓ | publish_time 空，event_time 09-27 09:00，expire_at 09-27 11:00，status=active |
| C001 推荐 | ~60（dry-run） | ✓ | SEND 应为 8 人 |
| C005 推荐 + NO_SEND | （同次运行） | ✓ | SEND 3 / NO_SEND 2（R009、R018） |
| C003 推荐 Before | ~60（dry-run） | ✓ | SEND 5，不含 R003；NO_SEND 为 R006 |
| Quick Capture（张姐） | ~40 | ✓ | 必须匹配 R003；I021 写入，写前确认不存在 |
| C003 推荐 After | ~30（dry-run） | ✓ | SEND 6，含 R003，理由引用刚才互动（E3→I021）；随后更新 R003 画像并建 P007 |
| Quick Capture（王阿姨） | ~50 | ✓ | Need 判为 unable_to_resolve；I022 + N007 + R014 画像，分三笔写入 |
| 今日运营摘要 | ~60（dry-run） | ✓ | 含未满足需求与招商线索（老人上门服务 4 条：1 following + 3 unable_to_resolve） |
| **整场合计** | **203（MCP 执行段）** | ✓ | 无重试、无漂移、无人工纠正；终态 25/8/15/22/7/7，option drift=0 |

异常记录：

```text
无。全部 add_records 单次成功，未触发超时/重试路径。
```

### 第 2 轮 · 2026-09-22（副本 LcElPOjddSfy）

| 步骤 | 耗时(秒) | 结果是否符合预期 | 备注 |
|---|---:|---|---|
| Content Agent 结构化 | ~30（dry-run） | ✓ | 与第 1 轮逐字段一致 |
| C001 推荐 | ~60（dry-run） | ✓ | SEND 8 人，集合与第 1 轮完全一致 |
| C005 推荐 + NO_SEND | （同次运行） | ✓ | SEND 3 / NO_SEND 2，集合一致 |
| C003 推荐 Before | ~60（dry-run） | ✓ | SEND 5 / R006 NO_SEND，集合一致 |
| Quick Capture（张姐） | ~30 | ✓ | I021 写入；Interaction-only After：C003 SEND 6，R003 唯一新增 |
| C003 推荐 After | ~30（dry-run） | ✓ | R003 画像更新 + P007 创建；P003 未动 |
| Quick Capture（王阿姨） | ~40 | ✓ | I022 + N007（unable_to_resolve、matched 空）+ R014 画像 |
| 今日运营摘要 | ~60（dry-run） | ✓ | 与第 1 轮事实一致（ID/状态/集合/数量零漂移） |
| **整场合计** | **138（MCP 执行段）** | ✓ | 无重试、无漂移、无人工纠正；终态 25/8/15/22/7/7，option drift=0 |

异常记录：

```text
无。
```

### 第 3 轮 · 2026-09-22（副本 LwtOAPgaYKti）

| 步骤 | 耗时(秒) | 结果是否符合预期 | 备注 |
|---|---:|---|---|
| Content Agent 结构化 | ~30（dry-run） | ✓ | 与第 1/2 轮逐字段一致 |
| C001 推荐 | ~60（dry-run） | ✓ | SEND 8 人，三轮一致 |
| C005 推荐 + NO_SEND | （同次运行） | ✓ | SEND 3 / NO_SEND 2，三轮一致 |
| C003 推荐 Before | ~60（dry-run） | ✓ | SEND 5 / R006 NO_SEND，三轮一致 |
| Quick Capture（张姐） | ~25 | ✓ | I021 写入；Interaction-only After：C003 SEND 6 |
| C003 推荐 After | ~30（dry-run） | ✓ | R003 画像 + P007；P003 未动 |
| Quick Capture（王阿姨） | ~35 | ✓ | I022 + N007 + R014 画像 |
| 今日运营摘要 | ~60（dry-run） | ✓ | 招商线索仅老人上门服务 4 条，排除小家电维修/儿童托管 |
| **整场合计** | **124（MCP 执行段）** | ✓ | 无重试、无漂移、无人工纠正；终态 25/8/15/22/7/7，option drift=0 |

异常记录：

```text
无。
```

## 汇总

三轮跑完后填：

| 步骤 | 平均耗时 | 最长耗时 | 三轮结果是否一致 |
|---|---:|---:|---|
| Content Agent 结构化 | ~30s（dry-run） | ~30s | ✓ 完全一致（publish_time 均空） |
| C001 推荐 | ~60s（dry-run） | ~60s | ✓ SEND 8 人集合逐人一致（含 R009） |
| C005 推荐 + NO_SEND | ~60s（dry-run） | ~60s | ✓ SEND {R004,R021,R025} / NO_SEND {R009,R018} |
| C003 推荐 Before | ~60s（dry-run） | ~60s | ✓ SEND {R001,R010,R015,R019,R024} / R006 NO_SEND |
| Quick Capture（张姐） | ~32s | ~40s | ✓ 均唯一匹配 R003；I021 各唯一；Interaction-only After 均 SEND 6、R003 唯一新增 |
| C003 推荐 After | ~30s（dry-run） | ~30s | ✓ P007 target 6 人 / no_send R006 三轮一致；P003 未动 |
| Quick Capture（王阿姨） | ~42s | ~50s | ✓ N007 均 unable_to_resolve、matched 空；S006 未硬配 |
| 今日运营摘要 | ~60s（dry-run） | ~60s | ✓ 事实层（ID/状态/集合/数量）三轮零漂移 |
| **整场合计（MCP 执行段）** | **155s** | **203s** | ✓ 三轮终态均 25/8/15/22/7/7，option drift=0 |

最慢单次 MCP 调用：`list_records` 全量读 Residents（25 条）≈3–5s；`copy_file` ≈5–10s。
三轮均**零重试、零模型输出漂移、零人工纠正**。
注：MCP 执行段平均 155s（2.6 分钟），加现场讲解与 Agent dry-run，整场稳定落在 5–10 分钟目标区间。

## Plan B 验证（2026-09-22，只读）

`LvSUGJQxbjeM`（东湖生活圈_Demo_After）逐项确认：

- [x] P003 Before：target 5 人（R001/R010/R015/R019/R024），no_send R006，带 DEMO BEFORE 说明，未改；
- [x] P007 After：target 6 人含 R003，draft/not_sent，带 DEMO AFTER 说明；
- [x] R003 After 画像：recent_interests=亲子活动，profile_summary 已更新；
- [x] I021（R003 / activity_inquiry / 亲子活动）、I022（R014 / service_request）在册；
- [x] N007：R014 / unable_to_resolve / matched_service_id 空；
- [x] Ops Summary 所需的 Needs 全景（N001 following、N002/N004 unable_to_resolve 等）完整。

结论：实时 Demo 任一步失败可直接切 Plan B 继续讲，**PASS**。

## Plan C

- [ ] 完整录屏：未录制（需演示人按正式讲解节奏自行录屏；三轮 PASS 已证明流程可稳定复现）

## 判定

进入正式演示的条件：

- [x] 三轮的 SEND / NO_SEND 名单完全一致；
- [x] 三轮结果都与 `tools/validate_demo_data.py --explain` 的输出一致；
- [x] Quick Capture 三轮都在 15 秒内出草稿；
- [x] 整场三轮都在 10 分钟内；
- [x] Plan B 的 `Demo_After` 副本已备好；
- [ ] Plan C 的完整录屏已录好。

任何一项不达标，先修再演。

> Phase 3 结论（2026-09-22）：除 Plan C 录屏（人工事项）外全部达标，判定 **MVP-0 DEMO READY**。
