# MVP-0 冻结取值表

> 主题标签在 `config/tags.md`。这份文件冻结**除主题标签以外**的全部受控取值。
>
> PRD v0.4.1 §7 只冻结了主题标签，但 `family_stage`、`target_population`、
> `region` 同样是多选 / 单选字段。不冻结它们，Content Agent 在结构化新内容时
> 会即兴造出「有孩子的家庭」「中老年人」「东湖及周边」这类近义值，
> 推荐规则的集合运算随即失效——这是无声的失效，表面上还在出名单。
>
> 校验由 `tools/validate_demo_data.py` 执行。

## 人群

`Residents.family_stage`（多选）：

```text
亲子家庭
老人家庭
年轻上班族
普通家庭
```

`Contents.target_population` / `Services.target_population`（多选），在以上四项之外增加：

```text
全部居民
```

规则：

- 「全部居民」不得与具体人群同时出现，语义矛盾（要么面向所有人，要么面向特定人群）。
- PRD §27 提到的「高频买菜家庭」「社区活跃居民」**不是** `family_stage`，
  它们通过 `long_term_interests` / `recent_interests` 表达，不要建成人群值。

## 区域

`Residents.community` / `Contents.region` / `Services.service_region`：

```text
东湖
东湖A区
东湖B区
东湖周边
```

规则：

- 不要写「东湖及周边」「东湖附近」「东湖一带」等变体。
- `东湖` 指市场本体及紧邻范围；`东湖A区 / 东湖B区` 是居住片区；`东湖周边` 是 15 分钟步行可达的其他区域。
- MVP-0 的推荐判定**不使用区域**（见 `config/recommendation-rules.md`），冻结取值只是为了防止词表漂移。

## 单选字段

| 字段 | 取值 |
|---|---|
| `Residents.status` | `active` / `low_active` / `dormant` / `lost` |
| `Contents.status` | `draft` / `active` / `expired` / `rejected` |
| `Contents.commercial_level` | `non_commercial` / `weak_commercial` / `service` / `promotion` |
| `Contents.risk_level` | `low` / `medium` / `high` |
| `Contents.content_type` | 同主题标签词表（`config/tags.md`） |
| `Interactions.interaction_type` | `content_reply` / `active_inquiry` / `service_inquiry` / `service_request` / `activity_inquiry` / `activity_signup` / `positive_feedback` / `negative_feedback` / `manual_followup` / `other` |
| `Interactions.related_type` | `content` / `service` / `need` / `activity` / 空 |
| `Interactions.sentiment` | `positive` / `neutral` / `negative` / 空 |
| `Needs.need_category` | 同主题标签词表 |
| `Needs.urgency` | `normal` / `high` |
| `Needs.status` | `new` / `following` / `resolved` / `unable_to_resolve` |
| `Services.service_category` | 同主题标签词表 |
| `Services.status` | `active` / `paused` / `unverified` |
| `Push_Plans.review_status` | `draft` / `approved` / `rejected` |
| `Push_Plans.send_status` | `not_sent` / `sent` / `cancelled` |

## 格式约定

| 约定 | 写法 | 例 |
|---|---|---|
| 多选字段分隔符 | 半角 `;` | `买菜生鲜;社区活动` |
| 居民名单分隔符 | 全角 `；` | `R003 张姐；R021 李阿姨` |
| 居民名单元素 | `<resident_id> <display_name>` | `R003 张姐` |
| 日期时间 | `YYYY-MM-DD HH:MM` | `2026-09-26 09:30` |
| 日期 | `YYYY-MM-DD` | `2026-09-26` |
| ID | 前缀 + 3 位数字 | `R001` `C003` `I021` `N007` `S001` `P006` |

> 居民名单用全角分号，是为了和多选字段的半角分号区分开：
> `target_residents` 在 SmartSheet 里是多行文本而不是多选，不能让导入工具误拆。
> 校验脚本两种分号都能读，但生成时一律用全角。

## 一致性约束

以下约束由 `tools/validate_demo_data.py` 强制，不是建议：

- `Needs.status = resolved` 必须有 `matched_service_id`；
- `Needs.status = unable_to_resolve` 必须没有 `matched_service_id`；
- `Residents.last_interaction_at` 必须等于该居民在 Interactions 里的最新一条时间；
- `Push_Plans` 里的居民名单，`resident_id` 与 `display_name` 必须和 Residents 表一致；
- `Interactions.related_id` 非空时必须有 `related_type`，且被引用的记录必须存在。

## 扩词流程

MVP-0 不建 Tags 表。需要新增取值时：

1. 人工改本文件或 `config/tags.md`；
2. 同步更新 `tools/donghu_demo.py` 里的词表常量；
3. 在 SmartSheet 对应字段里加选项；
4. 跑 `python3 tools/validate_demo_data.py` 确认没有破坏既有数据。

Agent **不得**自行新增取值。遇到无法归类的情况一律用「其他」并在
`operator_note` 里写明，交人工判断。
