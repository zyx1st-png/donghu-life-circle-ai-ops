# 东湖生活圈 MVP-0 Demo Seed Dataset 使用说明

> 对应需求文档：`PRD v0.4.1 — MVP-0 Demo Hardening Baseline`

## 1. 数据集目的

这份数据不是随机测试数据，而是为 5–10 分钟演示专门设计的故事化数据。它需要稳定展示四个核心价值：

1. AI 能把内容整理成结构化数据；
2. AI 能判断“该发给谁、不该发给谁”；
3. 居民一次新互动会改变下一轮推荐；
4. 居民需求可以沉淀为东湖后续服务引入 / 招商线索。

## 2. 六张工作表

```text
Residents
Contents
Interactions
Needs
Services
Push Plans
```

与 PRD v0.4.1 完全一致，不额外增加业务表。

## 3. 固定标签词表

所有 Agent 只允许使用 `config/tags.md` 中定义的标签。

## 4. 五个关键演示角色

### R003 张姐 — Before / After

初始：

```text
identify_note = 3栋张姐
long_term_interests = 社区活动
recent_interests = 空
```

现场 Quick Capture：

```text
3栋张姐问最近有没有适合小学生周末参加的活动。
```

新增 Interaction 后：

```text
recent_interests += 亲子活动
```

再跑 C003：R003 应进入推荐名单，并引用刚才的近期互动作为理由。

### R009 陈叔 — NO_SEND

```text
long_term_interests = 买菜生鲜;社区活动
avoid_topics = 优惠促销
```

对 C005“东湖商户周末满减促销”必须输出 NO_SEND。

### R014 王阿姨 — 未满足老人服务需求

现场输入：

```text
4栋王阿姨想找周末可以上门的老人助浴服务。
```

应形成 Interaction + Need。当前 Services 故意没有“上门助浴”，因此 Need 应进入 unable_to_resolve。

### R018 小刘 — 明确负反馈

已有 Interaction：

```text
最近消息有点多，先少发一点。
```

今日运营摘要中应提示近期不建议主动触达。

### R021 李阿姨 — 东湖自身内容精准触达

对 C001“东湖周末时令菜早市”应作为强推荐对象。

## 5. 推荐演示顺序

### Step 1 — 内容 Agent

使用 C003“周末儿童自然体验活动”，展示标题、摘要、标签、适用人群、时间、状态的结构化。

### Step 2 — 推荐 + NO_SEND

先展示 C001 对 R004 / R021 / R025 的推荐，再展示 C005 对 R009 的 NO_SEND。

### Step 3 — 张姐 Before / After

Before：C003 推荐名单没有 R003。

Quick Capture：

```text
3栋张姐问最近有没有适合小学生周末参加的活动。
```

After：重新推荐 C003，R003 进入名单。

### Step 4 — 王阿姨 Need

输入：

```text
4栋王阿姨想找周末可以上门的老人助浴服务。
```

系统匹配 R014，生成 Interaction 和 Need，查询 Services 后得到 unable_to_resolve。

### Step 5 — 今日运营摘要

建议问题：

```text
今天我最应该关注什么？
```

预期包含：有价值的今日 Push、张姐新增亲子活动关注、小刘近期负反馈、王阿姨老人助浴未满足，以及可能的东湖服务引入机会。

## 6. 当前 Push Plans 是 Before 状态

P003 是 C003 的 Before 推送草稿，目标中故意没有 R003。Quick Capture 后不要改历史 P003，建议生成新的 Push Plan 草稿（例如 P006），用于展示 Before P003 vs After P006。

## 7. 演示前检查

至少连续彩排 3 次，每次确认：

1. MCP 读取正常；
2. Quick Capture 能匹配 3栋张姐，而不是东门张姐；
3. C003 Before 不包含 R003；
4. After 包含 R003；
5. C005 对 R009 输出 NO_SEND；
6. 王阿姨需求找不到助浴服务；
7. 今日运营摘要能提到未满足需求。

## 8. 数据修改纪律

- Residents：`resident_id` 不修改。
- Interactions：只追加。
- 不要为了“还原演示”修改历史 `raw_note`。
- 重新彩排时使用 Demo Before 备份副本重新开始。

## 9. 演示备份

正式演示前保留：

```text
东湖生活圈_Demo_Before
东湖生活圈_Demo_After
```

优先实时演示；如模型或 MCP 卡顿，切换到 After 状态继续讲解，并准备完整录屏作为最终兜底。
