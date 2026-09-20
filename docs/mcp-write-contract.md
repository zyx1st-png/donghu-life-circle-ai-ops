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

```jsonc
{"field_values": [
  {"field": "display_name",        "text_value": "张姐"},
  {"field": "long_term_interests", "option_value": {"items": ["社区活动", "买菜生鲜"]}},
  {"field": "last_interaction_at", "string_value": "1790386200000"}
]}
```

| 字段类型 | 取值键 | 证据 |
|---|---|---|
| `text` | `text_value` | T0 A2 实测确认 |
| `select`（多选） | `option_value.items` 数组 | T0 A2 实测确认 |
| `singleSelect`（单选） | `option_value.items`（单元素） | **推断**，Build 第 0 步确认 |
| `dateTime` | `string_value`（毫秒时间戳字符串） | **推断**，Build 第 0 步确认 |

> 两处推断来自 T0 A2 记录的 `text_value / option_value / string_value` 三个键：
> 文本和多选已实测确认，剩下的按同族与排除法推定。
> **Build 第 0 步必须用一条探针记录确认**，确认后如有出入，
> 只需改 `tools/mcp_payloads.py` 里的 `VALUE_KEY` 一处。

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

### 漂移体检

每轮彩排前跑一次，比对线上真实选项和冻结词表：

```bash
python3 tools/mcp_payloads.py check-options --options demo/smartsheet-options.json
```

T0 B3 保证了漂移一定是无声的，所以这一步不能省。

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
平台不支持，只能由写入方填：

- 运营新建 Need 时，Ops Agent 把两者都填成当前时间；
- 后续修改 Need 时，只更新 `updated_at`；
- `created_at` 一旦写入不再修改。

## 9. 并发

T0 C5：并发写**不同**记录正常，无丢失。同一条记录的并发未测——
**同一条记录串行写**。

## 10. 视图

T0 C4：`add_view` 能建视图，但 grid 视图不支持传筛选条件。
`docs/sheet-setup.md` 里的运营视图**由人工在界面建**，不阻塞（PRD §37）。
