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

## 职责划分

| | 负责 |
|---|---|
| **本仓库** | 数据结构、Demo 数据、判定规则、Prompt、校验工具、演示脚本 |
| **WorkBuddy** | SmartSheet MCP 实际连接、建表、导入、Agent 运行、真实环境验证 |

仓库侧不假设任何 MCP 能力可用。需要真实环境确认的事项，
写成可执行的验证清单交给 WorkBuddy：`docs/t0-mcp-spike.md`。

## MVP-0 范围

只保留 6 张核心表：Residents、Contents、Interactions、Needs、Services、Push Plans。

只保留 3 个 Agent：Content Agent、Recommendation Agent、Ops Agent。

## 当前明确不做

PostgreSQL、FastAPI、独立前端、小程序、Signal 表、Push Target、微信客服机器人、
自动群聊分析、订单、支付、生产级幂等等均不属于 MVP-0。

## 目录

```text
PRD.md                          需求基线（v0.4.1）
README.md

config/
  tags.md                       固定主题标签词表（17 项）
  vocabulary.md                 人群 / 区域 / 单选字段的冻结取值
  recommendation-rules.md       推荐判定规则 —— Agent 和校验工具的共同依据
  operating-rules.md            运营原则与 Demo 剧情不变量

prompts/
  content-agent.md
  recommendation-agent.md
  ops-agent.md

docs/
  business-model.md             商业模式背景（business context，非实施规格）
  t0-mcp-spike.md               T0 MCP 能力验证清单 + 实测结果
  mcp-write-contract.md         SmartSheet 读写契约 —— Prompt 与工具的共同依据
  sheet-setup.md                建表规格与 Build 执行顺序
  demo-guide.md                 演示手册与台词
  rehearsal-log.md              彩排记录模板

demo/
  anchor.txt                    Demo 数据的日期锚点
  seed-data/*.csv               6 张表的演示数据
  smartsheet-options.json       Build 当时的选项 baseline 快照（**不是线上实时状态**）
  smartsheet-ids.json           file_id / sheet_id 记录

tools/
  donghu_demo.py                数据模型 + 字段类型 + 推荐规则引擎 + 时间转换
  validate_demo_data.py         数据校验 + 剧情不变量 + 预期结果打印
  shift_demo_dates.py           把整套 Demo 日期平移到新的演示日
  mcp_payloads.py               建表 / 写入 payload 生成、词表体检、写后核对
  test_mcp_payloads.py          mcp_payloads 的回归测试
```

## 常用命令

```bash
# 校验 seed 数据（改完数据必跑，全绿才进彩排）
python3 tools/validate_demo_data.py

# 看某条内容的逐人推荐判定，输出即"标准答案"
python3 tools/validate_demo_data.py --explain C003
python3 tools/validate_demo_data.py --explain C003 --after-quick-capture

# 演示改期：先平移日期，否则核心内容会过期、Before/After 演不了
python3 tools/shift_demo_dates.py --to 2026-10-11 --write

# ---- 与 SmartSheet 打交道 ----
python3 tools/mcp_payloads.py fields --out /tmp/fields.json        # 建表 payload
python3 tools/mcp_payloads.py check-options --options <fresh> --require-fresh  # 词表漂移体检
python3 tools/mcp_payloads.py records --table Residents            # 写入 payload
python3 tools/mcp_payloads.py verify --table Residents --dump d.json  # 写后核对
python3 tools/test_mcp_payloads.py                                 # 工具自测
```

工具只服务于演示稳定性，不是线上运行时。
推荐由 WorkBuddy 里的 Agent 完成；`tools/` 的作用是让"三次彩排结果一致"这件事可被验证。

## 规则与 Agent 的分工

```text
确定性规则  →  eligibility 与硬排除，产出候选集合
Agent       →  在候选集合内做语义判断（服务能力核对、文案）
运营        →  最终确认后才触达
```

因此 `--explain` 的输出：对非服务类内容是**最终标准答案**；
对服务类内容（`commercial_level = service`）是**候选基线**——
Agent 做完能力级核对后名单可以更窄，但不应更宽。

推荐结果分三层，不要混：

```text
ELIGIBLE     内容与居民适配
HOLD         适配，但今日不应主动触达（改日可发）
TARGET_TODAY = ELIGIBLE − HOLD    ← Push Plan 的当天执行名单
```

## 数据纪律

- 真实居民数据不得提交到本仓库。
- Demo Seed 全部为演示数据，联系方式为虚拟号码。
- `resident_id` 创建后不重命名。
- `Interactions.raw_note` 按追加事实处理，不为还原演示而修改历史记录。
- 密钥、Token、手机号、真实企微 ID 等不得提交 GitHub。

## 进度

- **T0**（2026-09-20）真实环境 PASS，BUILD GATE 开放。
- **Build Phase 1**（2026-09-21）六表建成、80 条 seed 写入、逐表 verify PASS。
  `singleSelect` 取值形状已确认，不再有未知数。

```text
Step 0 探针 ✓ → 建 6 张表 ✓ → 导出选项快照 ✓ → check-options ✓
→ 生成 records payload ✓ → 写入 ✓ → 读回 verify ✓
→ 人工建筛选视图
→ Content Agent
→ Recommendation Agent
→ Ops Agent / Quick Capture
→ 跑通 5 个 Demo 场景
→ 连续彩排 3 次（docs/rehearsal-log.md）
→ 录制备份 Demo
```

## 与 PRD 的差异

以下改动偏离了 PRD v0.4.1 的字面描述，原因写在对应文件里：

| 改动 | 位置 | 原因 |
|---|---|---|
| Push Plans 增加 NO_SEND / HOLD 共 4 列 | `docs/sheet-setup.md` | PRD §22 要求输出 NO_SEND 但没有字段存放；HOLD 被排出当天名单后，"内容其实适合他"这个判断也需要落到表里 |
| `Contents.region` 由单行文本改为单选 | `docs/sheet-setup.md` | 自由文本已经产生「东湖周边 / 东湖及周边」两种写法 |
| 冻结人群与区域词表 | `config/vocabulary.md` | PRD §7 只冻结了主题标签，其余多选字段同样会漂 |
| 写出完整推荐判定规则 | `config/recommendation-rules.md` | PRD 定义了展示什么，没有定义凭什么，导致同一条内容每次跑结果不同 |
| 重算全部 Push Plans 名单 | `demo/seed-data/Push_Plans.csv` | 原名单无法由任何成文规则复现，彩排时表里的 Before 和 Agent 实时输出对不上 |
| `active` 内容必须有 `expire_at` | `config/recommendation-rules.md` | 留空曾等同于"永不过期"，活动结束几周后仍会被推，且完全无声 |
| Need 判定看待办事项而非句式 | `prompts/ops-agent.md` | 「有没有靠谱的保洁？」是疑问句但确是真实需求，按句式切会系统性漏掉商业需求 |
| 未满足 Need 本身即推荐证据（E0） | `config/recommendation-rules.md` | `Needs` 是待办事项的权威来源；只认派生的 `recent_needs` 会让画像一被清理，真实需求就永远匹配不回本人 |
| `Needs.created_at` / `updated_at` 改普通 dateTime 字段并进 CSV | `docs/sheet-setup.md` | T0 C3 实测：系统时间字段的值 `list_records` 读不回，读不回就等于对 Agent 不存在 |
| Seed 不走 CSV 直导，改 payload 生成 + 写后核对 | `docs/mcp-write-contract.md` | T0 B6 实测：半角 `;` 在任何路径都不被拆；T0 A2：写入可能静默失败 |

## 商业模式背景

- [docs/business-model.md](./docs/business-model.md) — 机器可读的商业模式说明，用于业务背景、价值逻辑、收入方向与长期边界。
- 该文档是 **business context**，不是 MVP 实施规格；若与实现细节冲突，以 `PRD.md` 为准。

详细规格见 [PRD.md](./PRD.md)。
