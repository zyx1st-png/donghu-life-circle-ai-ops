# MVP-0 运营规则

## 核心原则

1. 宁可少发，不要乱发。
2. 无回复不等于负反馈。
3. 明确负反馈优先于 AI 推断。
4. 服务推荐优先由明确 Need 或 Service Intent 触发，且必须做能力级核对。
5. 未满足的需求包含 `unable_to_resolve`——当前没供给不等于这件事不用办了。
   `Needs` 是待办事项的权威来源，`recent_needs` 只是派生画像，清了画像不等于需求关闭。
6. Need 的判定看"有没有具体待办事项"，不看句式。
7. AI 只生成 Draft，运营确认后再执行居民触达。
8. 真实居民敏感数据不得提交到 GitHub。

## 数据纪律

- `resident_id` 创建后不重命名。
- Interactions 只追加；`raw_note` 不为演示还原而修改。AI 总结错了改 `ai_summary`。
- 系统时间字段优先使用 SmartSheet 自带字段。
- 标签、人群、区域只用冻结词表（`config/tags.md`、`config/vocabulary.md`）。
- Demo 数据可以重置，但应通过 Demo Before 备份重新开始。

## 判定规则

推荐的完整判定顺序见 `config/recommendation-rules.md`，那份文件是唯一依据。

三层语义必须分清：

```text
ELIGIBLE     内容与居民适配
HOLD         适配，但今日不应主动触达
TARGET_TODAY = ELIGIBLE − HOLD    ← Push Plan.target_residents 只能由它生成
```

内容时效契约（Prompt、规则引擎、校验脚本三处共同强制）：

```text
status = active  →  expire_at 必须存在且晚于当前时间
时效判断不了     →  保留 status = draft
```

## Demo 剧情不变量

以下每一条都由 `tools/validate_demo_data.py` 自动校验。
改动 seed 数据之后必须跑一次，全绿才算改完。

| 场景 | 不变量 |
|---|---|
| C003 Before | SEND 5 人，不含 `R003 张姐` |
| C003 Before | `R006 王老师` 进 NO_SEND，原因是已报名本条活动 |
| Quick Capture | `R003` 的 `recent_interests` 增加「亲子活动」 |
| C003 After | SEND 6 人，比 Before 只多出 `R003`，且她的依据来自近期互动而非长期兴趣 |
| C005 促销 | `R009 陈叔` NO_SEND，原因是 `avoid_topics = 优惠促销` |
| C001 早市 | `R009 陈叔` 仍在 SEND 名单里 —— NO_SEND 是按主题，不是按人 |
| Quick Capture | `R014 王阿姨` 的上门助浴需求在当前 Services 中无匹配（S006 陪诊不算） |
| 重名消歧 | 保留两位张姐，`identify_note` 不同 |
| HOLD | `R018 小刘` 在 C011 上判为 HOLD：内容适配但今日暂停 |
| HOLD | HOLD 居民不得出现在任何 `target_residents` 里，但保留在 `hold_residents` |
| 需求闭环 | `unable_to_resolve` 的 Need 仍算未满足；东湖引入新服务后能重新匹配回原居民 |
| 需求闭环 | 即使居民的 `recent_needs` / 兴趣 / 互动全被清空，仅凭 Needs 表里的记录也必须能重新匹配 |
| 时间边界 | `expire_at <= now` 即过期；未来时间的互动不得被当成近期证据 |
| 时效 | 至少 1 条 `expired` 内容 |
| 招商线索 | 至少 2 条 `unable_to_resolve` 的 Need |

## 演示日期

seed 的全部日期锚定在 `demo/anchor.txt`。

**演示改期时，先平移日期再彩排**，否则 C003 会过 `expire_at`，
推荐 Agent 会直接拒绝它，Before/After 这场核心戏就没了：

```bash
python3 tools/shift_demo_dates.py --to 2026-10-11 --write
python3 tools/validate_demo_data.py
```

## 每次改完数据

```bash
python3 tools/validate_demo_data.py
```

有 ERROR 就不要进彩排。
