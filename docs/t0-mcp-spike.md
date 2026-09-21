# T0 · 腾讯文档 SmartSheet MCP 能力验证

> **执行人：WorkBuddy**（仓库这边无法验证，必须在真实环境里跑）
> **目的**：在动手建表之前，确认 MCP 到底能做什么。
> **产出**：把下面每张表的「实测结果」列填掉，回填本文件并提交。

## 为什么要扩展 PRD 的 T0

PRD §37 的 T0 是四项：读取、新增、更新、创建字段。
这四项验证的是"能不能连上"，但连上之后仍有五个问题会直接决定 MVP-0 能不能做成，
而且都是**无声失效**——不报错，只是结果悄悄不对：

1. 多选字段的选项能不能由 MCP 固定？固定不了，整套冻结词表就只是一份文档，Agent 写什么都进得去。
2. 写入词表外的值会报错还是自动建选项？自动建 = 标签词表必然漂移。
3. 更新记录是局部更新还是整条覆盖？覆盖 = Quick Capture 更新 `recent_interests` 会抹掉 `profile_summary`。
4. CSV 导入时 `买菜生鲜;社区活动` 会拆成两个选项，还是变成一个叫"买菜生鲜;社区活动"的值？
   后者会让 25 条居民数据全部失真，而且表面上看不出来。
5. 一次读取能不能拿全 25 条居民？分页会让 Agent 只看到一部分人就出名单。

下面把验证项分成三组。**只有 A 组是真正的 BLOCKER**——B 组每一项都有明确的
人工兜底方案，FAIL 了只是改变实现方式，不应该挡住开工。

---

## A 组 · HARD BLOCKER

没有 workaround。任何一项 FAIL，都不要开始建表。

在一张**临时测试表**里做，不要用正式的六张表。

| 编号 | 验证内容 | 具体做法 | PASS 标准 | 实测结果 |
|---|---|---|---|---|
| A1 | 读取记录 | 读取测试表全部记录 | 拿到全部字段值，字段名与表头一致 | **PASS** · `list_records` 传 `field_titles` 后读回全部 5 个字段，字段名与表头一致；不传 `field_titles` 时 `field_values` 为空（易踩坑，见文末观测） |
| A2 | 新增记录 | 新增 1 条，含单行文本 / 多选 / 日期时间三种字段 | 三种字段都正确写入 | **PASS** · `add_records` 正确格式为 `field_values:[{field, text_value/option_value/string_value}]`；读回确认：文本✓、多选 2 个选项带选项 ID✓、日期时间毫秒时间戳原值✓。（注：第一次用错误格式调用也返回 success 但写入空记录——静默失败，见文末观测） |
| A3 | 更新记录 | 修改 A2 记录的某个字段 | 修改生效 | **PASS** · `update_records` 只改 `note` 一列，读回确认修改生效且其余字段全部保留 |
| A4 | 可靠取全 25 条 | 测试表塞 25 条，取出全部 | **能可靠取得完整 25 条即 PASS，需要翻页也算 PASS**，只要翻页逻辑稳定可复现 | **PASS** · 两种方式均可稳定取全 25 条：① 不传 limit 时一次返回全部 25 条（total<100）；② `limit=10` 翻 3 页（10+10+5），`has_more`/`next` 明确，T001–T025 顺序 3 次一致。limit 上限 100，>100 需 offset 翻页 |

> A4 的判定口径特意放宽。分页本身不是缺陷，**"取不全"或"翻页结果不稳定"才是**。
> 推荐 Agent 只要漏看几位居民就会出错名单，而且不会报错——
> 所以这里要验证的是"拿全"，不是"一次拿全"。
> 如果需要翻页，请在实测结果里写明每页条数和翻页方式，我们在 Prompt 里写死。

---

## B 组 · ADAPTATION REQUIRED

**FAIL 不阻塞开工**，但结论决定实现方式，必须记录清楚。

| 编号 | 验证内容 | 具体做法 | 需要记录 | FAIL 时的兜底 | 实测结果 |
|---|---|---|---|---|---|
| B1 | 创建字段 | 用 MCP 新建一个单行文本字段 | 能 / 不能 | 运营在界面手工建表 | **PASS（能）** · `add_fields` 可建全部类型字段（text/select/singleSelect/dateTime/createdTime…），并返回 field_id |
| B2 | 多选字段固定选项 | 新建多选字段并预设 3 个选项 | 选项能否按预设生成 | 运营手工建选项，**建完再导数据** | **PASS** · `property_select.options:[{text,style}]` 预设 3 选项，`list_fields` 读回确认选项、颜色、选项 ID 全部按预设生成 |
| B3 | 写入词表外的值 | 向 B2 字段写一个不在选项里的值 | 报错？静默丢弃？**自动新建选项**？ | 靠 Prompt 约束 + 校验脚本事后兜底 | **FAIL（最坏情况，已实测）** · 写入「宠物寄养」返回 success、不报错，`list_fields` 确认**自动新建了选项**（且原有多选值被整体替换）。词表必然漂移且无声 → **必须** Prompt 约束 + 彩排前校验脚本兜底 |
| B4 | 更新语义 | 只更新 1 个字段，检查其余字段 | 局部更新，还是整行覆盖 | 改成"读整条 → 本地合并 → 整条写回" | **PASS（局部更新）** · 只提交 1 个 field_value，读回确认其余字段原值不变，Quick Capture 可安全只改 `recent_interests` |
| B5 | 日期时间读写 | 写入 `2026-09-26 09:30` 再读回 | 值是否一致，时区是否漂移 | 记录偏移量和方向，数据侧统一补偿 | **PASS** · 写入东八区毫秒时间戳 `1790386200000`，读回逐字一致，API 层无时区偏移。Agent 写入前需自行把 `YYYY-MM-DD HH:MM` 转成东八区毫秒时间戳 |
| B6 | CSV 导入多选 | 用一列 `买菜生鲜;社区活动` 导入多选字段 | 拆成 2 个值？还是 1 个字符串？ | 按结论写转换脚本 | **FAIL（分号在任何路径都不会被拆）** · ① `manage.pre_import/async_import` 导入 CSV 生成的是**在线表格**（非智能表格），单元格原样保留整串 `买菜生鲜;社区活动`；② 把 `家政服务;维修服务` 作为单个选项文本写入多选字段，读回确认变成**一个名叫「家政服务;维修服务」的选项**。→ 仓库侧必须提供转换脚本：解析 CSV 把 `;` 拆成数组，用 `add_records` 以 `option_value.items` 逐条写入 |

### 各项为什么重要

**B3 如果是"自动新建选项"**——这是最坏的结果，因为它不报错。
标签词表会随 Agent 每次即兴发挥而扩散，集合运算逐渐失准，
而表面上推荐仍然照常出名单。此时必须在每轮彩排前加一步：导出数据跑校验脚本。

**B4 如果是整行覆盖**——Quick Capture 更新 `recent_interests` 会连带抹掉
`profile_summary` 和 `avoid_topics`。这不是大改动，但必须在 Prompt 里写死，
否则演示时会当场丢数据。

**B5 如果时区有偏移**——`expire_at` 是推荐规则第 0 步的依据。
偏移几小时就可能让当天的内容被判成过期。

**B6** —— `demo/seed-data/` 的 6 个 CSV 全部用半角 `;` 分隔多选值。
如果导入工具不这么理解，25 条居民数据会全部失真，而且表面上看不出来。
请把实际解析方式写清楚，我们在仓库侧提供对应的转换脚本。

---

## C 组 · 观测项

不判定 PASS / FAIL，只记录，用于后续调优。

| 编号 | 观测内容 | 需要记录 | 实测结果 |
|---|---|---|---|
| C1 | 读取延迟 | 连续读 3 次 25 条居民表，每次耗时（秒） | **OBSERVED** · Agent 侧无法精确计时（MCP 调用不经本地 shell）；体感每次 `list_records`（25 条 × 5 字段）约 1–2 秒，连续多次调用无超时、结果稳定。如需精确毫秒级数据，需在工程侧自行埋点 |
| C2 | 表的寻址方式 | 用表名还是内部 ID；建表后把 ID 记下来 | **OBSERVED** · 全部用内部 ID 寻址：`file_id`（文档）→ `sheet_id`（子表）→ `record_id`（记录）→ `field_id`（字段）；写记录时的 `field` 用字段标题匹配。本表：`file_id=LzEntBDtlsOI`，`sheet_id=gWeXhW` |
| C3 | 系统时间字段 | 有无「创建时间」「最后修改时间」类型，能否创建 / 读取 | **OBSERVED（字段可建、值读不回）** · `createdTime` / `modifiedTime` 字段可经 `add_fields` 创建（可配格式），但 `list_records` **不返回**这两个字段的值（`include_computed_values=true` 也不行）→ 建议按本文兜底方案：`Needs.created_at/updated_at` 用普通 dateTime 字段由运营录入 |
| C4 | 视图创建 | MCP 能否建筛选视图（不能就人工建） | **OBSERVED（半支持）** · `add_view` 可建 grid/kanban/gallery/gantt/calendar/form/query 视图（本表已建 `vUgfGB`），但 grid 视图**不支持传筛选条件**（读回 `filterSpec` 为空），筛选视图仍需人工在界面建 |
| C5 | 并发写入 | 同时写两条记录是否报错或丢失 | **OBSERVED** · 同一消息内并发调用两条不同记录的 `update_records` 均返回 success，读回两条都正确写入、无丢失、无报错（同记录并发未测；建议工程侧仍串行写同一记录） |

### C3 结论落实

实测确认系统字段的值读不回，因此 `Needs.created_at` / `updated_at`
已改为普通 dateTime 字段，并进入 `demo/seed-data/Needs.csv`。

读不回就等于对 Agent 不存在，所以值只能由写入方填。
这偏离了 PRD §29「不让 Agent 手动生成」，是平台能力所迫。
**完整规则见 `docs/mcp-write-contract.md` §8**，不要在别处另立一套。

---

## 回填格式

每项填 `PASS` / `FAIL` / `部分`，后面跟一句话说明。例：

```text
A4 | PASS | 每页 20 条，翻 2 页取全 25 条，3 次结果一致
B3 | FAIL | 写入词表外的值会自动新建选项，不报错 → 需要彩排前跑校验脚本
B4 | PASS | 局部更新，其余字段不受影响
B6 | 部分 | 分号被当成普通字符，需要改用换行分隔
```

## PASS 之后

**A 组全绿即可进入 Build**，顺序见 `docs/sheet-setup.md`。
B 组的 FAIL 项请把选定的兜底方案一并写进本文件，再开工——
带着未确认的假设建表，返工成本比多花半小时验证高得多。

---

## T0 RESULT（2026-09-20 实测回填）

```text
T0 RESULT
A HARD BLOCKER:
A1 读取记录    PASS  list_records(field_titles) 读回全部字段，字段名与表头一致
A2 新增记录    PASS  文本/多选/日期时间三类型均正确写入（需 field_values 正确格式）
A3 更新记录    PASS  单字段修改生效，其余字段保留
A4 取全 25 条  PASS  一次读取即返回 25 条；limit=10 翻 3 页亦可稳定取全，3 次结果一致

B ADAPTATION:
B1 创建字段            PASS（能）   add_fields 全类型可建
B2 多选预设选项        PASS         property_select.options 预设生效
B3 词表外值            FAIL→已实测  自动新建选项、不报错、原值被替换 → Prompt 约束 + 彩排前校验脚本
B4 更新语义            PASS         局部更新，不覆盖整行
B5 日期时间            PASS         毫秒时间戳写入读回逐字一致，无时区漂移
B6 CSV 多选导入        FAIL→已实测  分号在任何路径都不被拆：CSV 导入生成在线表格（整串字符串），
                                    写入多选字段则生成一个带分号的选项 → 仓库侧转换脚本必需

C OBSERVATIONS:
C1 读取延迟    约 1–2 秒/次（Agent 侧无法精确计时，多次稳定无超时）
C2 寻址方式    全部内部 ID：file_id → sheet_id → record_id → field_id；写字段值用字段标题
C3 系统时间    createdTime/modifiedTime 字段可创建，但 list_records 读不回值 → Needs 用普通 dateTime 字段
C4 视图        add_view 可建视图但 grid 不支持筛选条件 → 筛选视图人工建
C5 并发写入    两条并发写不同记录均成功无丢失（同记录并发未测，建议串行）

BUILD GATE: PASS（A 组全绿，可以开工建表）
REQUIRED ADAPTATIONS:
1. Seed 导入不走 CSV 直导：仓库提供转换脚本，解析 demo/seed-data/*.csv 的半角 ; 多选列，
   调 add_records 以 option_value.items 数组写入（B6）。
2. 标签词表防漂移双保险（B3）：Prompt 只用冻结词表 + 每次写操作后读回校验 /
   彩排前跑校验脚本比对 list_fields 选项集合与 config/tags.md。
3. Needs.created_at / updated_at 不用系统字段，改普通 dateTime 由运营录入（C3）。
4. Agent 写日期时间须自行换算东八区毫秒时间戳（B5）。
5. 每个关键写操作后必须 list_records 读回确认——MCP 对格式错误静默返回 success（见下）。

EVIDENCE:
- 测试 SmartSheet：T0-MCP-Spike测试表20260920
  file_id=LzEntBDtlsOI，sheet_id=gWeXhW
  https://docs.qq.com/smartsheet/DTHpFbnRCRHRsc09J（保留作 T0 evidence，未删除，全部为假数据）
- B6 导入产物：在线表格 t0-import-test，file_id=LhcZxLkAnFsK
  https://docs.qq.com/sheet/DTGhjWnhMa0FuRnNL（单元格保留整串「买菜生鲜;社区活动」）

关键 MCP 实际行为（写后必读回的原因）：
- add_records 用错误 values 格式调用 → 返回 success 但写入空记录（静默失败）。
- update_records 返回的 trace 不含字段级确认 → 必须 list_records 读回核对。
- list_records 不传 field_titles → field_values 为空（不是报错，是空）。
- 多选字段写入未注册的 text → 自动新建选项（is_quick_add 字段读回为 false，但行为属实）。

NEXT OWNER: Opus / WorkBuddy
```

> 以上结论全部来自 2026-09-20 晚在真实腾讯文档智能表格 + tencent-docs MCP 上的实际调用与读回，
> 未凭文档或经验推断。
