# 东湖生活圈 AI 运营系统

当前基线：**PRD v0.4.1 — MVP-0 Demo Hardening Baseline**

## 当前目标

本仓库只服务于东湖生活圈 AI 运营系统的最小验证 / 展示版本。

MVP-0 需要在 5–10 分钟内稳定演示：

1. 内容自动结构化；
2. 推荐给谁 + 为什么 + NO_SEND；
3. Quick Capture 一句话记录居民互动；
4. 同一内容在居民新互动前后的推荐变化；
5. 居民 Need 与东湖服务引入 / 招商机会。

## 技术基线

- 腾讯文档智能表格：MVP-0 数据与运营界面
- WorkBuddy：Agent、MCP 操作端、自然语言入口
- 企业微信：居民触达与人工沟通
- GitHub：PRD、Prompt、Demo 数据与开发资产

## MVP-0 范围

只保留 6 张核心表：

- Residents
- Contents
- Interactions
- Needs
- Services
- Push Plans

只保留 3 个 Agent：

- Content Agent
- Recommendation Agent
- Ops Agent

## 当前明确不做

PostgreSQL、FastAPI、独立前端、小程序、Signal 表、Push Target、微信客服机器人、自动群聊分析、订单、支付、生产级幂等等均不属于 MVP-0。

## 目录

```text
PRD.md
README.md

docs/
  demo-guide.md

prompts/
  content-agent.md
  recommendation-agent.md
  ops-agent.md

config/
  tags.md
  operating-rules.md

demo/
  seed-data/
    Residents.csv
    Contents.csv
    Interactions.csv
    Needs.csv
    Services.csv
    Push_Plans.csv
```

## 数据纪律

- 真实居民数据不得提交到本仓库。
- Demo Seed 全部为演示数据。
- `resident_id` 创建后不重命名。
- `Interactions.raw_note` 按追加事实处理，不为还原演示而修改历史记录。
- 密钥、Token、手机号、真实企微 ID 等不得提交 GitHub。

## 开工顺序

```text
T0 MCP 基础验证
→ 建 6 张表
→ 导入 Demo Seed
→ 固定标签
→ Content Agent
→ Recommendation Agent
→ Ops Agent / Quick Capture
→ 5 个 Demo 场景
→ 连续彩排 3 次
```

详细规格见 [PRD.md](./PRD.md)。

## 商业模式背景

- [docs/business-model.md](./docs/business-model.md) — 机器可读的商业模式说明，用于业务背景、价值逻辑、收入方向与长期边界。
- 该文档是 **business context**，不是 MVP 实施规格；若与实现细节冲突，以 `PRD.md` 为准。
