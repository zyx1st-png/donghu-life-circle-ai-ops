# SmartSheet MCP 读写契约

> **唯一依据来源**：2026-09-20 的 T0 实测（`docs/t0-mcp-spike.md`）。
> 本文是 Prompt、工具和建表规格共同遵守的一份契约——
> 同一条规则不要在三个 Prompt 里各写一遍，那样必然漂。
>
> 三个 Agent Prompt 都指向这里。改平台行为先改这里。

## 一句话

> **"调用返回 success" 不等于 "数据写进去了"。**

T0 实测到三种**静默失败**——不报错，只是结果不对：

| 行为 | 实测结果 |
|---|---|
| `add_records` 用错误的 `field_values` 格式 | 返回 success，**写出空记录** |
| 多选字段写入未注册的值 | 返回 success，**自动新建选项**，且原有多选值被整体替换 |
| `list_records` 不传 `field_titles` | 不报错，**`field_values` 返回空** |

所以本契约的核心是：**每一次关键写入之后必须读回核对**。

---

## 1. 寻址

```text
file_id（文档） → sheet_id（子表） → record_id（记录） → field_id（字段）
```

全部用内部 ID。**但写记录时 `field_values[].field` 用的是字段标题，不是 field_id。**

建完表后把 `file_id` / `sheet_id` 记进 `demo/smartsheet-ids.json`，不要靠记忆。

## 2. 字段取值的形状

> **以 2026-09-21 Build Phase 1 实测为准。** 本节曾按 T0 阶段的记录写成
> "text_value 是纯字符串"，正式 Build 时被 MCP 参数校验直接拒绝。
> 下面是真实建成六张表、写入 80 条记录、逐表 verify PASS 的形状。

### 写记录

```jsonc
{"field_values": [
  {"field": "display_name",
   "text_value": {"items": [{"text": "张姐", "type": "text"}]}},

  {"field": "long_term_interests",                       // 多选
   "option_value": {"items": [{"text": "社区活动"}, {"text": "买菜生鲜"}]}},

  {"field": "status",                                    // 单选，同样是 items 数组
   "option_value": {"items": [{"text": "active"}]}},

  {"field": "last_interaction_at",
   "string_value": "1790386200000"}                      // 东八区毫秒时间戳字符串
]}
```

| 字段类型 | 取值键 | 形状 | 证据 |
|---|---|---|---|
| `text` | `text_value` | `{items:[{text, type:"text"}]}` | Phase 1 实测 |
| `select`（多选） | `option_value` | `{items:[{text}]}` | Phase 1 实测 |
| `singleSelect`（单选） | `option_value` | `{items:[{text}]}`（单元素） | **Phase 1 实测 PASS** |
| `dateTime` | `string_value` | 毫秒时间戳字符串 | T0 A2 + B5，Phase 1 复核 |

**`text_value` 和 `option_value.items` 都不接受纯字符串**，必须是对象数组。
纯字符串连 MCP 的参数校验都过不了——这和 T0 A2 那种"返回 success 写出空记录"
不是一回事：那是 `field_values` 整体形状错，这是字段级形状错，会直接报错。

`singleSelect` 曾是 T0 唯一没覆盖的未知数，Phase 1 探针已确认：
写值形状与多选完全相同，就是 `option_value.items:[{text}]`。

### 建字段

**建字段的属性键和写值的取值键是两套东西，不要混。**

| 字段类型 | 建字段属性 | 说明 |
|---|---|---|
| `text` | 无 | |
| `select` | `property_select: {options:[{text}]}` | |
| `singleSelect` | `property_single_select: {options:[{text}]}` | 用 `property_select` 报 **22020** |
| `dateTime` | `property_date_time: {format: "..."}` | **必填**，不带报 **22018** |

Demo 用的 format：一般字段 `yyyy-mm-dd hh:mm`，`Push_Plans.push_date` 用 `yyyy-mm-dd`。

**一批 `add_fields` 里只要有一个字段被拒，同批其它字段也不会创建。**
所以建表失败时不要逐个补，先把整批 payload 改对再重来——
否则会像 Phase 1 那样留下空壳表（`LQMxvbFFUkRB`，可人工删）。

这些都由 `tools/mcp_payloads.py fields` 生成，不需要手写。

## 3. 日期时间

**东八区毫秒时间戳。** API 层无时区偏移（T0 B5 写入读回逐字一致）。

```text
"2026-09-26 09:30"（东八区） → 1790386200000
```

校准证据：T0 B5 实际写入的就是这个值，`tools/donghu_demo.py` 的
`to_cst_millis()` 对同一输入输出一致。

**换算集中在 `to_cst_millis()` / `from_cst_millis()` 里做。**
Agent 在 Prompt 里不要自己推公式——三个 Prompt 各写一份，迟早有一份算错，
而算错 8 小时的 `expire_at` 会让当天的内容被判成过期，且不报错。

Agent 运行时自行换算的自检方法：换算完之后立刻反算回可读时间，
和原始字符串逐字对比，不一致就不要写。

## 4. 读取

**`list_records` 必须传 `field_titles`**，列出所有需要的字段。
不传不会报错，只是 `field_values` 为空——推荐 Agent 会因此看到一张空表，
然后照常输出一个空名单。

分页（T0 A4）：

- 不传 `limit` 时一次返回全部（总数 < 100）；
- `limit` 上限 100；
- 超过 100 条用 `offset` 翻页，`has_more` / `next` 明确可用。

MVP-0 的 6 张表最大 25 条，**一次读取即可**。
Interactions 会随演示增长，超过 100 条时必须改成翻页——
漏读几条互动不会报错，只会让推荐名单悄悄变少。

## 5. 多选字段：fail-closed

T0 B3 实测：写入未注册的值 → 静默新建选项 + 原值被替换。
所以**不能靠 Prompt 自觉**，要在写之前拦住：

```text
建表（预设选项） → list_fields 导出选项快照 → 生成 payload 时逐值校验
                                              ↳ 有未注册值就拒绝生成
```

```bash
python3 tools/mcp_payloads.py records --table Residents --options demo/smartsheet-options.json
```

没有快照时工具直接拒绝工作，这是有意的：宁可不生成，也不要生成一份
会污染词表的 payload。

### 选项快照格式

`list_fields` 的原始返回直接存成 JSON 即可，工具能解析两种形态：

```jsonc
// 形态 1：list_fields 原样
{"Residents": {"fields": [
  {"field_id": "fldXXX", "field_title": "family_stage", "field_type": "select",
   "property_select": {"options": [{"id": "optAAA", "text": "亲子家庭"}]}}
]}}

// 形态 2：归一后（手工整理时用这个更省事）
{"Residents": {"family_stage": {"亲子家庭": "optAAA", "老人家庭": "optBBB"}}}
```

解析不出来时工具会明确报错说它找了哪些键，**不会猜**。

### 漂移体检：必须用当场导出的新快照

**`demo/smartsheet-options.json` 是 Build Phase 1 的 baseline snapshot，
不是线上实时状态。** 它记录的是"建表那一刻线上长什么样"，
之后 Agent 每写一次多选字段都可能把线上改掉，而仓库里这份文件不会变。

拿仓库里的旧 baseline 跑一遍然后宣布"线上没有漂移"，
等于用上个月的体检报告证明今天没病。**T0 B3 保证了漂移一定是无声的**，
所以这个自欺的代价是：词表已经脏了，而你以为它是干净的。

正确流程，每轮彩排 / 关键 Agent 测试前：

```text
1. WorkBuddy 对 6 张表调 list_fields，导出 fresh live snapshot
2. python3 tools/mcp_payloads.py check-options --options <fresh snapshot>
3. PASS 之后才能继续
```

**工具不连 MCP，只负责比较。** 导出是 WorkBuddy 的事，
Python 这边拿到什么就比什么——所以喂给它哪份快照，决定了结论有没有意义。

发现漂移时：在 SmartSheet 界面删掉多出来的选项，重新导出，再跑一次。
不要直接改仓库里的 baseline 去迁就线上——那是把证据改成结论。

baseline 的用途只有两个：Build 当时的存档，以及生成 records payload 时
的 fail-closed 依据（那一步发生在 Build 期间，baseline 就是当时的实时状态）。

## 6. 写 → 读回 → 核对

**每个关键写操作之后**（建表、导 seed、Quick Capture 写 Interaction、
更新居民画像、写 Push Plan）：

1. 执行写入；
2. `list_records` 带 `field_titles` 读回刚写的记录；
3. 逐字段核对，**特别是多选和日期时间**；
4. 不一致就停下来查，不要继续往下走。

批量导入用工具核对：

```bash
python3 tools/mcp_payloads.py verify --table Residents --dump 读回结果.json
```

它会报出四类问题：

```text
[空记录] 读回一条没有 resident_id 的记录——典型的静默写入失败（T0 A2）
[缺失]   R014 没有写进去
[不符]   R003.recent_interests 期望 []，读回 ['亲子活动']
[多余]   线上存在 seed 里没有的 R099
```

单条写入（Quick Capture）由 Agent 自己读回核对，核对项见各 Prompt。

## 7. 局部更新是安全的

T0 B4 实测：`update_records` 只提交一个 `field_value` 时，其余字段保持原值。

所以 Quick Capture 更新 `recent_interests` **不需要**先读整条再整条写回。
但更新完仍然要读回确认——安全的是"不会覆盖别的字段"，
不是"一定写成功了"。

## 8. 系统时间字段不可用

T0 C3：`createdTime` / `modifiedTime` 字段能建，但 `list_records` 读不回值
（`include_computed_values=true` 也不行）。

因此 `Needs.created_at` / `updated_at` 改为**普通 dateTime 字段**，
已进入 `demo/seed-data/Needs.csv`。

这偏离了 PRD §29「不让 Agent 手动生成 created_at / updated_at」——
读不回就等于对 Agent 不存在，值只能由写入方维护。

**本仓库唯一的规则，其他地方不要另立一套：**

| 动作 | `created_at` | `updated_at` |
|---|---|---|
| 新建 Need | 当前时间 | 当前时间 |
| 修改 Need | **保持原值不变** | 当前时间 |

两者都是普通 dateTime 字段，写入时同样要换算成东八区毫秒时间戳（§3）。

## 9. 平台默认字段

真实 SmartSheet 每张表都会自带一个平台字段 **`智能表列`**，
不是我们建的，也不在 `SCHEMA` 里。

所以报字段数时要分清，混着说会让人以为建漏了或建多了：

```text
business field count = SCHEMA 里的业务字段数
physical field count = business + 1（平台默认的 智能表列）
```

| 表 | business | physical |
|---|---:|---:|
| Residents | 13 | 14 |
| Services | 11 | 12 |
| Contents | 16 | 17 |
| Interactions | 11 | 12 |
| Needs | 10 | 11 |
| Push_Plans | 14 | 15 |

**它不是数据层问题，不要因此重建任何东西。**
`check-options` 只比对 `SCHEMA` 里声明的字段，多出来的平台字段不会报错。

如果平台 UI 支持隐藏该列，**正式 Demo 前作为 UI housekeeping 顺手隐藏**，
让运营看到的表干净一点。隐藏不了也不影响任何判定。

## 10. 并发

T0 C5：并发写**不同**记录正常，无丢失。同一条记录的并发未测——
**同一条记录串行写**。

## 11. 视图

T0 C4：`add_view` 能建视图，但 grid 视图不支持传筛选条件。
`docs/sheet-setup.md` 里的运营视图**由人工在界面建**，不阻塞（PRD §37）。
