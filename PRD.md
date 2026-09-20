# 东湖生活圈 AI 运营系统 PRD v0.4.1
## MVP-0 Demo Hardening Baseline

> **文档类型**：最小验证 / 展示版需求文档  
> **适用对象**：项目负责人、WorkBuddy、CodeBuddy/Codex、运营人员  
> **版本**：v0.4.1  
> **日期**：2026-09-20  
> **阶段定位**：MVP-0 / Demo / 最小闭环验证  
> **核心目标**：用 5–10 分钟稳定演示“AI 随互动越来越懂居民”，并展示对东湖运营和服务组织的直接价值  
> **继承关系**：本版继承 v0.4 的最小范围，不恢复任何生产级复杂功能

---

# 0. 本版本只解决什么

v0.4.1 不增加新的系统模块。

本轮只强化 8 件事：

1. 增加居民辨识字段 `identify_note`；
2. 固定所有字段类型，不再出现 `TEXT / SELECT` 等待定写法；
3. 冻结一套 MVP-0 固定标签词表；
4. 把“越来越懂居民”改造成可直接看到的 Before / After A/B 演示；
5. 增加 `NO_SEND` 演示；
6. 使用故事化模拟数据，而不是随机测试数据；
7. 增加东湖自身内容、居民需求与招商 / 服务机会的连接；
8. 增加演示稳定性保障。

除此之外：

> **不新增功能，不扩大 MVP-0。**

---

# 1. 一句话产品定义

东湖生活圈 AI 运营系统，是一套利用：

```text
腾讯文档智能表格
+
WorkBuddy
+
企业微信
```

构建的社区生活 AI 运营机制。

它要证明的是：

> **AI 能帮助社区运营人员从“统一群发”逐渐走向“知道什么值得发、适合发给谁、居民最近需要什么”。**

---

# 2. MVP-0 最核心验证问题

第一版只回答 5 个问题：

1. AI 能否自动整理社区生活信息；
2. AI 能否判断“什么内容适合谁”；
3. 运营是否能用一句话快速记录居民互动；
4. **居民发生一次有意义互动后，同一条内容的下一轮推荐结果是否会合理变化；**
5. AI 是否能生成真正可执行的运营摘要和需求机会。

---

# 3. MVP-0 Definition of Done

只要能够稳定完成以下 5 个演示，本版本即视为完成。

## DoD-1 内容结构化

录入一条原始生活信息：

```text
原始文字 / URL
↓
内容 Agent
↓
Contents 结构化记录
```

---

## DoD-2 推荐 + NO_SEND

AI 对 10–30 个居民生成：

```text
推荐给谁
为什么推荐
建议怎么说

以及：

不推荐给谁
为什么不推荐
```

必须至少出现 1 个可解释的 `NO_SEND`。

---

## DoD-3 Quick Capture

运营输入一句自然语言：

> 3栋张姐问最近有没有适合小学生周末参加的活动。

系统在尽量 15 秒内形成：

```text
居民匹配
↓
Interaction 草稿
↓
运营确认
↓
写入
↓
更新近期画像
```

---

## DoD-4 Before / After 推荐变化

同一条“周末儿童自然体验活动”：

### Before

张姐初始无亲子相关画像，因此不进入推荐名单。

### Quick Capture 后

新增：

```text
张姐近期主动咨询“小学生周末活动”
```

### After

重新运行同一内容推荐：

```text
张姐进入推荐名单
+
推荐理由明确引用近期互动
```

这是本 Demo 最重要的产品时刻。

---

## DoD-5 今日运营摘要

系统可以回答：

```text
今天有什么值得发？
哪些居民值得关注？
有哪些真实需求？
哪些需求目前没有供给？
这些需求对东湖服务引入 / 招商有什么启发？
```

---

# 4. 当前技术基线

MVP-0 使用：

```text
腾讯文档智能表格
=
核心数据存储
+
运营查看界面

WorkBuddy
=
AI Agent
+
MCP 操作端
+
自然语言入口
+
运营摘要
```

企业微信当前承担：

```text
居民触达
+
人工沟通
```

不要求自动读取全部企微聊天，也不要求自动群发。

---

# 5. 当前明确不做

本版本继续明确不做：

- PostgreSQL；
- FastAPI；
- 独立 Web 后台；
- 小程序 / App；
- 编号回复；
- 微信客服 AI 自动回复；
- 自动读取全部企微私聊 / 群聊；
- 企微客户标签自动同步；
- Signal 独立表；
- Push Target 独立表；
- 生产级幂等；
- run_id 全链路；
- 完整服务商治理；
- 订单 / 支付 / 库存；
- CRM；
- 积分 / 分佣；
- 共建人 Agent；
- 复杂权限；
- 向量数据库；
- LangChain / LangGraph。

---

# 6. MVP-0 仅保留 6 张核心表

```text
01 Residents
02 Contents
03 Interactions
04 Needs
05 Services
06 Push Plans
```

不增加第 7 张业务表。

---

# 7. 固定标签词表

MVP-0 不建设 Tags 表。

三个 Agent 和所有多选字段统一使用以下固定词表：

```text
亲子活动
老人服务
买菜生鲜
餐饮美食
家政服务
维修服务
社区活动
健康活动
教育学习
文化娱乐
运动健身
交通出行
天气提醒
公共服务
便民信息
优惠促销
```

无法归类时：

```text
其他
```

禁止 Agent 自行生成近义新标签，例如：

```text
育儿
儿童活动
亲子娱乐
孩子活动
```

以上必须统一归入：

```text
亲子活动
```

---

# 8. Residents 居民表

字段类型本版本正式冻结。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| resident_id | 单行文本 | 是 | 稳定内部 ID，不修改 |
| display_name | 单行文本 | 是 | 常用称呼 |
| identify_note | 单行文本 | 否 | 例如“3栋张姐” |
| community | 单选 | 否 | 社区 / 小区 |
| family_stage | 多选 | 否 | 例如亲子家庭、老人家庭 |
| long_term_interests | 多选 | 否 | 仅使用固定标签词表 |
| recent_interests | 多选 | 否 | 仅使用固定标签词表 |
| recent_needs | 多选 | 否 | 仅使用固定标签词表 |
| avoid_topics | 多选 | 否 | 仅使用固定标签词表 |
| last_interaction_at | 日期时间 | 否 | 最近互动 |
| profile_summary | 多行文本 | 否 | AI / 人工可读摘要 |
| operator_note | 多行文本 | 否 | 运营备注 |
| status | 单选 | 是 | active / low_active / dormant / lost |

## 8.1 resident_id 规则

`resident_id`：

- 创建后不得重命名；
- 不使用 display_name 作为主 ID；
- Demo Seed 使用固定 ID：`R001` ～ `R025`。

---

# 9. Quick Capture 居民识别

运营输入：

> 3栋张姐问最近有没有适合小学生周末参加的活动。

运营 Agent 优先使用：

```text
identify_note
+
display_name
```

匹配居民。

规则：

### 唯一匹配

直接形成草稿。

### 多人匹配

列出候选，例如：

```text
找到两位“张姐”：
R003 3栋张姐
R017 东门张姐

请选择。
```

### 无匹配

询问：

```text
是否选择已有居民，或新建居民？
```

MVP-0 不要求自动创建新居民。

---

# 10. Residents 数据原则

不保存：

- 人格；
- 心理标签；
- 政治倾向；
- 详细健康诊断；
- 与社区运营无关的敏感信息。

无回复：

> 不自动解释为“不感兴趣”。

---

# 11. Contents 内容表

| 字段 | 类型 | 必填 |
|---|---|---:|
| content_id | 单行文本 | 是 |
| title | 单行文本 | 是 |
| source | 单行文本 | 否 |
| source_url | URL | 否 |
| summary | 多行文本 | 是 |
| content_type | 单选 | 是 |
| topic_tags | 多选 | 否 |
| target_population | 多选 | 否 |
| region | 单行文本 | 否 |
| publish_time | 日期时间 | 否 |
| event_time | 日期时间 | 否 |
| expire_at | 日期时间 | 否 |
| commercial_level | 单选 | 是 |
| risk_level | 单选 | 是 |
| status | 单选 | 是 |
| operator_note | 多行文本 | 否 |

status：

```text
draft
active
expired
rejected
```

commercial_level：

```text
non_commercial
weak_commercial
service
promotion
```

risk_level：

```text
low
medium
high
```

---

# 12. Demo 内容要求

Demo Seed 至少包含：

- 2–3 条东湖自身内容；
- 亲子活动；
- 买菜生鲜；
- 天气 / 公共提醒；
- 老人服务；
- 家政维修；
- 1 条促销内容，用于演示 NO_SEND；
- 1 条即将 / 已过期内容，用于演示基础时效判断。

东湖自身内容示例：

```text
东湖周末时令菜早市
东湖亲子食育体验
东湖便民服务日
```

---

# 13. Interactions 互动表

| 字段 | 类型 | 必填 |
|---|---|---:|
| interaction_id | 单行文本 | 是 |
| resident_id | 单行文本 | 是 |
| interaction_time | 日期时间 | 是 |
| interaction_type | 单选 | 是 |
| related_type | 单选 | 否 |
| related_id | 单行文本 | 否 |
| raw_note | 多行文本 | 是 |
| ai_summary | 多行文本 | 否 |
| topic_tags | 多选 | 否 |
| sentiment | 单选 | 否 |
| created_by | 单行文本 | 否 |

interaction_type：

```text
content_reply
active_inquiry
service_inquiry
service_request
activity_inquiry
activity_signup
positive_feedback
negative_feedback
manual_followup
other
```

sentiment：

```text
positive
neutral
negative
```

---

# 14. Interactions 的关键规则

Interactions：

> **只追加，不修改历史事实。**

如果运营发现 AI 总结有误：

- 不修改原始 `raw_note`；
- 可以修正 `ai_summary`；
- 或新增一条人工说明。

后续如果升级 MVP-1：

> 可以从 Interactions 重新推导 Signal。

---

# 15. Quick Capture 主路径

目标：

> 运营人员不需要打开 SmartSheet 逐字段录入。

示例：

> 3栋张姐问最近有没有适合小学生周末参加的活动。

AI 草稿：

```text
resident_id: R003
interaction_type: activity_inquiry
raw_note: 原句
ai_summary: 张姐主动询问适合小学生参加的周末活动
topic_tags: 亲子活动
sentiment: neutral
```

运营确认后：

```text
写入 Interactions
↓
更新 Residents.recent_interests
↓
更新 profile_summary
```

---

# 16. 近期画像更新原则

MVP-0 不建设 Signal 表。

运营 Agent 根据近期 Interactions 更新：

```text
recent_interests
recent_needs
profile_summary
last_interaction_at
```

但：

- 不覆盖长期稳定兴趣；
- 不把一次无回复解释为负反馈；
- 明确负反馈优先；
- 人工可以修正。

---

# 17. Needs 需求表

| 字段 | 类型 | 必填 |
|---|---|---:|
| need_id | 单行文本 | 是 |
| resident_id | 单行文本 | 是 |
| need_category | 单选 | 是 |
| need_summary | 多行文本 | 是 |
| urgency | 单选 | 否 |
| status | 单选 | 是 |
| matched_service_id | 单行文本 | 否 |
| followup_note | 多行文本 | 否 |
| created_at | 系统创建时间 | 是 |
| updated_at | 系统最后修改时间 | 是 |

status：

```text
new
following
resolved
unable_to_resolve
```

urgency：

```text
normal
high
```

---

# 18. Need 生成原则

普通咨询不自动生成 Need。

例如：

> 周末有什么活动？

只形成 Interaction。

例如：

> 有没有人周末能上门给老人助浴？

形成：

```text
Interaction
+
Need
```

---

# 19. Services 服务表

| 字段 | 类型 | 必填 |
|---|---|---:|
| service_id | 单行文本 | 是 |
| provider_name | 单行文本 | 是 |
| service_name | 单行文本 | 是 |
| service_category | 单选 | 是 |
| service_summary | 多行文本 | 是 |
| price_description | 单行文本 | 否 |
| service_region | 多选 | 否 |
| target_population | 多选 | 否 |
| contact | 单行文本 | 否 |
| status | 单选 | 是 |
| operator_note | 多行文本 | 否 |

status：

```text
active
paused
unverified
```

---

# 20. 服务推荐边界

优先由：

```text
明确 Need
+
明确服务咨询
```

触发。

例如：

```text
看过养老资讯
≠
推荐助浴
```

而：

```text
明确询问上门助浴
→
可以匹配服务
```

---

# 21. Push Plans 推送计划表

| 字段 | 类型 | 必填 |
|---|---|---:|
| push_id | 单行文本 | 是 |
| push_date | 日期 | 是 |
| content_id | 单行文本 | 是 |
| target_residents | 多行文本 | 否 |
| target_segment | 单行文本 | 否 |
| recommend_reason | 多行文本 | 是 |
| message_text | 多行文本 | 是 |
| review_status | 单选 | 是 |
| send_status | 单选 | 是 |
| operator_note | 多行文本 | 否 |

`target_residents` 为演示可读格式：

```text
R003 张姐；R011 小王；R021 李阿姨
```

不使用数组或复杂关联。

review_status：

```text
draft
approved
rejected
```

send_status：

```text
not_sent
sent
cancelled
```

---

# 22. 推荐 Agent 必须同时回答 SEND 和 NO_SEND

推荐结果不只展示：

> 给谁发。

还必须能展示：

> 谁不应该收到，以及原因。

例如：

```text
R009 陈叔
NO_SEND

原因：
该居民明确设置“优惠促销”为 avoid_topics，
本内容属于 promotion。
```

---

# 23. Demo 2：推荐 + NO_SEND

演示内容：

> 东湖周末时令菜早市 / 一条促销内容。

推荐 Agent 输出：

### SEND

```text
R021 李阿姨
原因：
长期关注买菜生鲜和社区活动。
```

### NO_SEND

```text
R009 陈叔
原因：
明确不希望接收优惠促销。
```

演示目的：

> **系统不是为了发更多，而是为了少发错。**

---

# 24. Demo 3：Before / After A/B

这是整场演示最重要的场景。

## Step A — Before

内容：

> `C003 周末儿童自然体验活动`

初始 `R003 张姐`：

```text
family_stage：普通家庭
long_term_interests：社区活动
recent_interests：空
```

第一次运行推荐：

```text
张姐不进入推荐名单
```

或优先级很低。

---

## Step B — Quick Capture

运营输入：

> 3栋张姐问最近有没有适合小学生周末参加的活动。

系统：

```text
匹配 R003
↓
新增 Interaction
↓
recent_interests += 亲子活动
↓
profile_summary 更新
```

---

## Step C — After

再次对同一条 `C003` 推荐：

```text
R003 张姐进入推荐名单
```

理由：

> 张姐近期主动咨询过适合小学生参加的周末活动，与本活动主题和人群高度相关。

演示目的：

> **用同一条内容证明系统会随着互动改变判断。**

---

# 25. Demo 4：真实需求 → 服务匹配 / 未满足

居民：

```text
R014 王阿姨
```

输入：

> 王阿姨想找一个周末可以上门的老人助浴服务。

系统：

```text
Interaction
+
Need
```

如果 Services 无匹配：

```text
status = unable_to_resolve
```

运营摘要中出现：

> 老人上门助浴存在未满足需求。

---

# 26. Demo 5：今日运营摘要 + 东湖机会

运营问：

> 今天我最应该关注什么？

系统回答应包含类似：

```text
1. 今天有 2 条内容值得推送。
2. R003 张姐近期新增“亲子活动”关注。
3. R018 小刘最近有明确负反馈，今天不建议主动触达。
4. R014 王阿姨的老人助浴需求目前没有匹配服务。
5. 近期居民需求中，老人上门服务、儿童周末活动和维修服务重复出现，可作为后续服务引入 / 招商线索。
```

---

# 27. Demo Seed 人群设计

25 个居民不随机生成。

至少分为：

```text
亲子家庭
老人家庭
年轻上班族
高频买菜家庭
社区活跃居民
```

并设置 4 个关键角色：

## R003 张姐

用途：

> Before / After 推荐变化。

初始不带“亲子活动”标签。

---

## R009 陈叔

用途：

> NO_SEND。

设置：

```text
avoid_topics = 优惠促销
```

---

## R014 王阿姨

用途：

> 老人上门助浴未满足 Need。

---

## R018 小刘

用途：

> 明确负反馈 / 今日不触达。

---

## R021 李阿姨

用途：

> 东湖时令菜、早市活动精准推荐。

---

# 28. 东湖自身利益如何在 Demo 中出现

不增加商业系统。

只通过两种方式展示。

## A. 精准触达东湖内容

例如：

```text
东湖周末时令菜早市
```

优先推荐给：

```text
买菜生鲜
+
社区活动
```

相关居民。

不是全量群发。

---

## B. 居民需求 → 服务引入 / 招商线索

运营摘要展示：

```text
近期重复出现但当前无供给的生活需求
```

例如：

```text
老人上门服务
儿童周末托管
修鞋 / 修伞
小家电维修
```

输出：

> 可作为后续服务引入、活动设计或招商线索。

---

# 29. 系统时间字段原则

能使用 SmartSheet 系统字段时：

```text
创建时间
最后修改时间
```

统一使用系统字段。

不让 Agent 手动生成 `created_at / updated_at`。

---

# 30. 演示稳定性保障

MVP-0 是 Demo，因此稳定演示本身属于产品需求。

---

## 30.1 每个核心动作至少提前跑 3 次

记录：

```text
平均耗时
最长耗时
结果是否稳定
```

重点测试：

```text
内容结构化
推荐 Before
Quick Capture
推荐 After
运营摘要
```

---

## 30.2 演示数据冻结

正式演示前：

- 不临时随机换居民；
- 不临时换标签；
- 不临时换核心内容；
- 不修改关键剧情角色。

保证 Demo 可重复。

---

## 30.3 三层演示保障

### Plan A — 实时演示

优先现场真实运行。

### Plan B — 预置状态

如果某一步 MCP / 模型明显卡顿：

> 切换到已准备好的下一状态数据继续演示。

建议保留：

```text
Demo Before
Demo After
```

两个备份状态。

### Plan C — 完整录屏

正式演示前准备一份 5–10 分钟完整录屏。

用于现场网络或平台异常时兜底。

---

# 31. 演示时间目标

整场：

> **5–10 分钟。**

建议节奏：

```text
1 分钟：产品问题和价值
1 分钟：内容自动整理
2 分钟：推荐 + NO_SEND
2 分钟：张姐 Before / Quick Capture / After
1–2 分钟：王阿姨 Need
1–2 分钟：今日运营摘要 + 东湖机会
```

---

# 32. 对外展示表达

不要重点讲：

- MCP；
- Agent 数量；
- SmartSheet 技术；
- 数据库；
- Prompt。

核心只讲：

> **AI 帮运营人员每天找到真正值得居民知道的信息，判断什么适合谁，并随着居民互动逐渐理解居民真正需要什么。**

---

# 33. MVP-0 成功指标

不设复杂 KPI。

只判断：

### 内容整理
是否减少复制、摘要、分类工作。

### 推荐
推荐对象和理由是否大部分“说得通”。

### Quick Capture
是否明显比逐字段录表更轻。

### Before / After
互动后同一内容推荐是否出现合理变化。

### NO_SEND
是否能合理解释为什么“不发”。

### 东湖价值
是否能从居民需求中看出服务、活动或招商机会。

### 演示理解
非开发人员能否在 5–10 分钟后理解系统价值。

---

# 34. 仍然暂不做

本轮评审不得将以下功能重新带回：

```text
Signal 表
Push Target 表
企微标签同步
PostgreSQL
FastAPI
微信客服机器人
自动群聊分析
生产级幂等
订单
支付
独立前端
```

---

# 35. MVP-1 触发条件

只有 MVP-0 Demo 得到明确正反馈，并准备真实扩大运行时，再进入 MVP-1。

例如：

```text
真实居民扩大到 50–100 人
开始连续运行数周
运营需要更强自动化
Interaction 数量持续增加
Push 需要更精确追踪
```

届时再补：

- Signal；
- Push Batch / Target；
- 幂等；
- 企微标签；
- 更完整权限；
- 群画像增强；
- 自动聊天；
- 生产级 Workflow。

---

# 36. 第一轮实施顺序

```text
1. T0 MCP 基础验证
2. 建 6 张表
3. 导入 Demo Seed Dataset
4. 固定标签选项
5. 建 5 个运营视图
6. 内容 Agent
7. 推荐 Agent
8. 运营 Agent / Quick Capture
9. 跑 Before / After
10. 跑 NO_SEND
11. 跑 Need 场景
12. 跑运营摘要
13. 连续彩排 3 次
14. 录制备份 Demo
```

---

# 37. T0 Technical Spike

只验证：

```text
读取记录
新增记录
更新记录
创建字段
```

四项 PASS 即开工。

创建视图如果 MCP 不方便：

> 运营人员手工创建，不阻塞。

---

# 38. WorkBuddy / CodeBuddy 第一轮启动指令

```text
项目：
东湖生活圈 AI 运营系统 MVP-0 Demo

基线：
PRD v0.4.1

当前目标不是生产系统。
只构建一个稳定、可重复、5–10 分钟可展示的最小闭环。

第一步执行 T0：
1. 连接腾讯文档 SmartSheet MCP；
2. 读取测试记录；
3. 新增测试记录；
4. 更新测试记录；
5. 创建测试字段。

四项核心能力 PASS 后进入 Build。

Build 只允许建立 6 张表：
- Residents
- Contents
- Interactions
- Needs
- Services
- Push Plans

必须使用 PRD 固定字段类型和固定标签词表。

随后导入 Demo Seed Dataset。

只实现 3 个 Agent：
1. Content Agent
2. Recommendation Agent
3. Ops Agent

必须跑通：
1. Content 结构化
2. 推荐 + NO_SEND
3. Quick Capture
4. 同内容 Before / After 推荐变化
5. Need + 今日运营摘要

不要增加：
- PostgreSQL
- FastAPI
- Signal 表
- Push Target
- 企微自动标签
- 微信客服机器人
- 自动群聊
- 生产级复杂功能

所有 Interactions：
只追加，不修改 raw_note。

所有 resident_id：
稳定、不重命名。

正式演示前：
连续彩排至少 3 次，并记录每个核心步骤耗时与异常。
```

---

# 39. 最终原则

本版本唯一目标：

> **让别人看懂、看信：这个系统真的可以随着居民互动越来越懂社区，而且这种理解可以反过来帮助内容运营、居民服务和东湖服务组织。**

因此当前所有决策服从：

```text
少做
做好
稳定
可展示
有前后变化
有业务价值
```

---

**END OF PRD v0.4.1 — MVP-0 Demo Hardening Baseline**
