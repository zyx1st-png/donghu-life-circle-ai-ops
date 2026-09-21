# SmartSheet 建表规格

> **执行人：WorkBuddy**，在 `docs/t0-mcp-spike.md` 的 A 组全部 PASS 之后。
>
> 字段名、顺序必须与 `demo/seed-data/*.csv` 的表头完全一致，
> 否则导入会错列。`tools/validate_demo_data.py` 会校验本文件与 CSV 表头的一致性。

## Build 执行顺序

T0 已 PASS（`docs/t0-mcp-spike.md`）。按下面的顺序执行，**不要跳步**——
每一步的产物都是下一步的前提。读写行为见 `docs/mcp-write-contract.md`。

```text
0. 探针：确认 singleSelect 的取值键
1. 建 6 张表（被引用的表先建）
2. list_fields 导出选项快照 → demo/smartsheet-options.json
3. check-options 体检（线上选项 vs 冻结词表）
4. 生成 records payload（有未注册值会拒绝生成）
5. add_records 写入
6. list_records 读回 → verify 核对
7. 人工建筛选视图（T0 C4：grid 视图不支持传筛选条件）
```

### Step 0 · 探针（5 分钟，别省）

T0 A2 测了单行文本 / 多选 / 日期时间三种类型，也记录了对应的三个取值键，
B5 又单独验证了日期时间读回逐字一致。所以这三者都有实测支撑。

**唯一没被 T0 覆盖的是 `singleSelect`**——它不在那三种类型里。
六张表有 20 多个单选字段，这一处不确认，建表和写入会整片出错。

1. 在临时表里建一个 `singleSelect` 字段，预设 2 个选项；
2. 用 `option_value.items:["选项A"]` 写入；
3. `list_records` 读回，确认写进去的是那个选项，而不是空值或新建的选项。

读回不对就换键再试，**确认结果改到 `tools/mcp_payloads.py` 的 `VALUE_KEY` 一处**，
不要在别处打补丁。

顺手把 `dateTime` 也复核一遍（`string_value:"1790386200000"`，对应东八区
`2026-09-26 09:30`，可肉眼核对）——那是复核既有证据，不是补验证，但它失败时无声，
多花一分钟值得。

### Step 1 · 建表顺序

被引用的表先建，避免引用悬空：

```text
1. Residents
2. Services
3. Contents
4. Interactions   （引用 Residents / Contents / Services）
5. Needs          （引用 Residents / Services）
6. Push Plans     （引用 Residents / Contents）
```

`add_fields` 的 payload 直接生成，不要手抄——
17 个标签 × 多个字段，手抄必错：

```bash
python3 tools/mcp_payloads.py fields --out /tmp/fields.json
python3 tools/mcp_payloads.py fields --table Residents      # 只看一张
```

## 选项字段的准备

单选和多选字段的选项，取值一律来自 `config/tags.md` 和 `config/vocabulary.md`。

**T0 B2 PASS**：`property_select.options:[{text, style}]` 可以在建字段时直接预设，
`list_fields` 读回确认选项与选项 ID 全部按预设生成。所以选项由 MCP 建，不用手工。

但 **T0 B3 FAIL**：写入未注册的值会静默新建选项，还会把原有多选值整体替换。
所以预设选项只是第一道防线，第二道是写入前的 fail-closed 校验（Step 3–4）。

主题标签词表（17 项）在多个字段里重复使用，建议先在一处建好再复制：

```text
亲子活动 老人服务 买菜生鲜 餐饮美食 家政服务 维修服务 社区活动 健康活动
教育学习 文化娱乐 运动健身 交通出行 天气提醒 公共服务 便民信息 优惠促销 其他
```

---

## 01 Residents

| 字段 | 类型 | 必填 | 选项 / 说明 |
|---|---|---|---|
| resident_id | 单行文本 | 是 | `R001`–`R025`，创建后不重命名 |
| display_name | 单行文本 | 是 | 常用称呼 |
| identify_note | 单行文本 | 否 | 如「3栋张姐」，Quick Capture 靠它消歧 |
| community | 单选 | 否 | 区域词表 |
| family_stage | 多选 | 否 | 人群词表（不含「全部居民」） |
| long_term_interests | 多选 | 否 | 主题标签词表 |
| recent_interests | 多选 | 否 | 主题标签词表 |
| recent_needs | 多选 | 否 | 主题标签词表 |
| avoid_topics | 多选 | 否 | 主题标签词表 |
| last_interaction_at | 日期时间 | 否 | 必须等于该居民最新一条 Interaction 的时间 |
| profile_summary | 多行文本 | 否 | 人可读摘要 |
| operator_note | 多行文本 | 否 | 运营备注 |
| status | 单选 | 是 | `active` / `low_active` / `dormant` / `lost` |

## 02 Services

| 字段 | 类型 | 必填 | 选项 / 说明 |
|---|---|---|---|
| service_id | 单行文本 | 是 | `S001`– |
| provider_name | 单行文本 | 是 | |
| service_name | 单行文本 | 是 | |
| service_category | 单选 | 是 | 主题标签词表 |
| service_summary | 多行文本 | 是 | **要写清能办什么、不办什么**，匹配时按这里判断 |
| price_description | 单行文本 | 否 | |
| service_region | 多选 | 否 | 区域词表 |
| target_population | 多选 | 否 | 人群词表 + 全部居民 |
| contact | 单行文本 | 否 | Demo 用虚拟号码 |
| status | 单选 | 是 | `active` / `paused` / `unverified` |
| operator_note | 多行文本 | 否 | |

## 03 Contents

| 字段 | 类型 | 必填 | 选项 / 说明 |
|---|---|---|---|
| content_id | 单行文本 | 是 | `C001`– |
| title | 单行文本 | 是 | |
| source | 单行文本 | 否 | |
| source_url | URL | 否 | |
| summary | 多行文本 | 是 | |
| content_type | 单选 | 是 | 主题标签词表 |
| topic_tags | 多选 | 否 | 主题标签词表 |
| target_population | 多选 | 否 | 人群词表 + 全部居民 |
| region | 单选 | 否 | 区域词表 |
| publish_time | 日期时间 | 否 | |
| event_time | 日期时间 | 否 | 活动发生时间 |
| expire_at | 日期时间 | 否 | **推荐规则第 0 步依赖它，实际必填** |
| commercial_level | 单选 | 是 | `non_commercial` / `weak_commercial` / `service` / `promotion` |
| risk_level | 单选 | 是 | `low` / `medium` / `high` |
| status | 单选 | 是 | `draft` / `active` / `expired` / `rejected` |
| operator_note | 多行文本 | 否 | |

> **与 PRD 的差异**：PRD §11 把 `region` 定为单行文本。这里改成单选，
> 取值见 `config/vocabulary.md`。原因是 seed 数据里已经出现了「东湖周边」和
> 「东湖及周边」两种写法，自由文本会让区域词表无声漂移。

## 04 Interactions

| 字段 | 类型 | 必填 | 选项 / 说明 |
|---|---|---|---|
| interaction_id | 单行文本 | 是 | `I001`– |
| resident_id | 单行文本 | 是 | |
| interaction_time | 日期时间 | 是 | |
| interaction_type | 单选 | 是 | 见 `config/vocabulary.md`（10 项） |
| related_type | 单选 | 否 | `content` / `service` / `need` / `activity` |
| related_id | 单行文本 | 否 | 填了就必须有 `related_type` |
| raw_note | 多行文本 | 是 | **运营原句，只追加不修改** |
| ai_summary | 多行文本 | 否 | 总结错了改这里，不要改 `raw_note` |
| topic_tags | 多选 | 否 | 主题标签词表 |
| sentiment | 单选 | 否 | `positive` / `neutral` / `negative` |
| created_by | 单行文本 | 否 | |

## 05 Needs

| 字段 | 类型 | 必填 | 选项 / 说明 |
|---|---|---|---|
| need_id | 单行文本 | 是 | `N001`– |
| resident_id | 单行文本 | 是 | |
| need_category | 单选 | 是 | 主题标签词表 |
| need_summary | 多行文本 | 是 | 写清要办的具体事项 |
| urgency | 单选 | 否 | `normal` / `high` |
| status | 单选 | 是 | `new` / `following` / `resolved` / `unable_to_resolve` |
| matched_service_id | 单行文本 | 否 | `resolved` 必填；`unable_to_resolve` 必须留空 |
| followup_note | 多行文本 | 否 | |
| created_at | 日期时间 | 是 | 普通 dateTime，不是系统字段 |
| updated_at | 日期时间 | 是 | 普通 dateTime，不是系统字段 |

> **与 PRD 的差异**：PRD §17 / §29 要求这两列用 SmartSheet 系统字段，
> 并明确"不让 Agent 手动生成"。
> **T0 C3 实测**：`createdTime` / `modifiedTime` 字段能建，但 `list_records`
> 读不回它们的值（`include_computed_values=true` 也不行）。
> 读不回就等于对 Agent 不存在，因此改为普通 dateTime 字段，并已进入
> `demo/seed-data/Needs.csv`。写入方填值的规则见 `docs/mcp-write-contract.md` §8。

## 06 Push Plans

| 字段 | 类型 | 必填 | 选项 / 说明 |
|---|---|---|---|
| push_id | 单行文本 | 是 | `P001`– |
| push_date | 日期 | 是 | |
| content_id | 单行文本 | 是 | |
| target_residents | 多行文本 | 否 | **当天执行名单** = 适配 − HOLD。`R003 张姐；R021 李阿姨`，全角分号 |
| target_segment | 单行文本 | 否 | 人群描述 |
| recommend_reason | 多行文本 | 是 | |
| message_text | 多行文本 | 是 | |
| no_send_residents | 多行文本 | 否 | 格式同 `target_residents`。主题禁忌等硬排除 |
| no_send_reason | 多行文本 | 否 | |
| hold_residents | 多行文本 | 否 | 内容适配、但今日暂停主动触达的居民 |
| hold_reason | 多行文本 | 否 | |
| review_status | 单选 | 是 | `draft` / `approved` / `rejected` |
| send_status | 单选 | 是 | `not_sent` / `sent` / `cancelled` |
| operator_note | 多行文本 | 否 | |

> **与 PRD 的差异**：新增 4 列，分成两组。
>
> `no_send_residents` / `no_send_reason` —— PRD §22 要求推荐 Agent 必须输出 NO_SEND，
> 但 v0.4.1 的 Push Plans 没有地方存它，结果是整场演示里最有说服力的那个判断
> 只存在于对话框里，一回表格就看不见了。
>
> `hold_residents` / `hold_reason` —— `target_residents` 是当天的执行名单，
> 必须排除今日 HOLD 的居民，否则会出现"名单里有他、同时又写着今天不要联系他"的矛盾。
> 但被排除的原因不能丢：HOLD 和 NO_SEND 的后续动作完全不同（HOLD 改日可以再发，
> NO_SEND 这个主题就不发了），所以分成两组而不是混在一起。
>
> 加 4 列比加一张表便宜得多，也让「少发错」在 SmartSheet 里可以被直接指着看。

---

## Step 2–6 · 导入 Demo Seed

**不要用 CSV 直接导入。** T0 B6 实测：`manage.pre_import` / `async_import`
导入 CSV 生成的是**在线表格**而不是智能表格，多选列原样保留整串
`买菜生鲜;社区活动`；把整串作为单个选项文本写入多选字段，
则会生成一个名叫「买菜生鲜;社区活动」的选项。

半角 `;` 在任何路径都不会被拆。所以 seed 在仓库侧先拆成数组，
再用 `add_records` 逐条写。

### Step 2 · 导出选项快照

建完表后立刻做，这是后面所有写入的前提：

```bash
# 对 6 张表分别调 list_fields，把原始返回存成一个 JSON
# 结构见 docs/mcp-write-contract.md §5
demo/smartsheet-options.json
```

顺手把 `file_id` / `sheet_id` 记进 `demo/smartsheet-ids.json`，不要靠记忆。

### Step 3 · 词表体检

```bash
python3 tools/mcp_payloads.py check-options --options demo/smartsheet-options.json
```

必须全绿再往下。这一步会抓出建表时漏建的选项和多建的选项——
两者都会让后面的写入静默出错。

### Step 4 · 生成写入 payload

```bash
for t in Residents Services Contents Interactions Needs Push_Plans; do
  python3 tools/mcp_payloads.py records --table $t --out /tmp/$t.records.json
done
```

任何一个取值不在线上已注册的选项里，**工具会拒绝生成并指出是哪条记录的哪个字段**。
这是 fail-closed：宁可不生成，也不要生成一份会污染词表的 payload。

### Step 5 · 写入

按建表顺序逐表 `add_records`。**不要跨表并行**——
T0 C5 只验证了并发写不同记录安全，表级别的顺序依赖仍在。

### Step 6 · 读回核对

```bash
# 每张表：list_records 带 field_titles 读回全部字段，存成 JSON
python3 tools/mcp_payloads.py verify --table Residents --dump /tmp/Residents.dump.json
```

**这一步不能省。** T0 A2 实测：`add_records` 格式错误时返回 success
但写出空记录——"调用成功"和"写进去了"是两件事。

verify 会报四类问题：`[空记录]` `[缺失]` `[不符]` `[多余]`。

条数核对：居民 25 / 内容 15 / 互动 20 / 需求 6 / 服务 8 / 推送 6。

### Step 6b · 剧情抽查

verify 全绿之后，再人工确认一条：

> `R003` 的 `recent_interests` **必须为空**，`long_term_interests` 只有「社区活动」。

这条错了，Before/After 整场戏就没了。

## 运营视图

MCP 建不了就人工建，不阻塞（PRD §37）：

| 视图 | 表 | 筛选 |
|---|---|---|
| 今日可发内容 | Contents | `status = active` 且 `expire_at` 晚于今天 |
| 待审推送 | Push Plans | `review_status = draft` |
| 今日暂停触达 | Push Plans | `hold_residents` 非空 |
| 未解决需求 | Needs | `status` 为 `new` / `following` |
| 无供给需求 | Needs | `status = unable_to_resolve` |
| 近期活跃居民 | Residents | 按 `last_interaction_at` 倒序 |
