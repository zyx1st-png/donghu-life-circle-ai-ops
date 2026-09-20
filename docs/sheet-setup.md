# SmartSheet 建表规格

> **执行人：WorkBuddy**，在 `docs/t0-mcp-spike.md` 的 A 组全部 PASS 之后。
>
> 字段名、顺序必须与 `demo/seed-data/*.csv` 的表头完全一致，
> 否则导入会错列。`tools/validate_demo_data.py` 会校验本文件与 CSV 表头的一致性。

## 建表顺序

被引用的表先建，避免引用悬空：

```text
1. Residents
2. Services
3. Contents
4. Interactions   （引用 Residents / Contents / Services）
5. Needs          （引用 Residents / Services）
6. Push Plans     （引用 Residents / Contents）
```

## 选项字段的准备

单选和多选字段的选项，取值一律来自 `config/tags.md` 和 `config/vocabulary.md`。

- T0 的 A5 PASS → 用 MCP 建字段时直接预设选项；
- A5 FAIL → 运营人员在 SmartSheet 界面手工把选项建好，**建完再导数据**。
  先导数据后建选项，多选值会变成游离文本。

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

**另加两个系统字段**（不在 CSV 里，导入后由系统自动维护）：

| 字段 | 类型 |
|---|---|
| created_at | 系统创建时间 |
| updated_at | 系统最后修改时间 |

> T0 的 B2 若确认系统字段不可用，改为普通日期时间字段，由运营录入。
> Agent 无论如何不生成这两个值。

## 06 Push Plans

| 字段 | 类型 | 必填 | 选项 / 说明 |
|---|---|---|---|
| push_id | 单行文本 | 是 | `P001`– |
| push_date | 日期 | 是 | |
| content_id | 单行文本 | 是 | |
| target_residents | 多行文本 | 否 | `R003 张姐；R021 李阿姨`，全角分号 |
| target_segment | 单行文本 | 否 | 人群描述 |
| recommend_reason | 多行文本 | 是 | |
| message_text | 多行文本 | 是 | |
| no_send_residents | 多行文本 | 否 | 格式同 `target_residents` |
| no_send_reason | 多行文本 | 否 | |
| review_status | 单选 | 是 | `draft` / `approved` / `rejected` |
| send_status | 单选 | 是 | `not_sent` / `sent` / `cancelled` |
| operator_note | 多行文本 | 否 | |

> **与 PRD 的差异**：新增 `no_send_residents` 和 `no_send_reason` 两列。
> PRD §22 要求推荐 Agent 必须输出 NO_SEND，但 v0.4.1 的 Push Plans 没有地方存它，
> 结果是整场演示里最有说服力的那个判断只存在于对话框里，
> 一切回表格就看不见了。加两列比加一张表便宜得多，
> 也让「少发错」这件事在 SmartSheet 里可以被直接指着看。

---

## 导入 Demo Seed

1. 先确认 T0 的 B1 结论：CSV 里的半角 `;` 会不会被拆成多选值。
   不会的话先按 B1 记录的方式转换。
2. 按建表顺序导入 6 个 CSV。
3. 导入后逐表核对条数：居民 25 / 内容 15 / 互动 20 / 需求 6 / 服务 8 / 推送 5。
4. 抽查 3 条多选字段，确认是多个选项而不是一整串文本。
5. 抽查 `R003`：`recent_interests` 必须为空，`long_term_interests` 只有「社区活动」。
   这条错了，Before/After 整场戏就没了。

## 运营视图

MCP 建不了就人工建，不阻塞（PRD §37）：

| 视图 | 表 | 筛选 |
|---|---|---|
| 今日可发内容 | Contents | `status = active` 且 `expire_at` 晚于今天 |
| 待审推送 | Push Plans | `review_status = draft` |
| 未解决需求 | Needs | `status` 为 `new` / `following` |
| 无供给需求 | Needs | `status = unable_to_resolve` |
| 近期活跃居民 | Residents | 按 `last_interaction_at` 倒序 |
