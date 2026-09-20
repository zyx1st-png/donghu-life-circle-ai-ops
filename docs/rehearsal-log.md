# 彩排记录

> PRD §30.1：每个核心动作至少提前跑 3 次，记录平均耗时、最长耗时、结果是否稳定。
>
> 演示稳定性本身就是 MVP-0 的产品需求。这份记录的用途是**在现场之前**
> 发现哪一步会卡、哪一步结果会飘。

## 每轮开始前

```bash
python3 tools/validate_demo_data.py          # 必须全绿
```

从 `Demo_Before` 备份恢复数据，确保每轮起点一致。

## 轮次记录

复制下面这张表，每彩排一轮填一份。

### 第 N 轮 · YYYY-MM-DD

| 步骤 | 耗时(秒) | 结果是否符合预期 | 备注 |
|---|---:|---|---|
| Content Agent 结构化 | | | |
| C001 推荐 | | | SEND 应为 8 人 |
| C005 推荐 + NO_SEND | | | SEND 3 / NO_SEND 2（R009、R018） |
| C003 推荐 Before | | | SEND 5，不含 R003；NO_SEND 为 R006 |
| Quick Capture（张姐） | | | 必须匹配 R003 |
| C003 推荐 After | | | SEND 6，含 R003，理由引用刚才互动 |
| Quick Capture（王阿姨） | | | Need 判为 unable_to_resolve |
| 今日运营摘要 | | | 含未满足需求与招商线索 |
| **整场合计** | | | 目标 5–10 分钟 |

异常记录：

```text
（哪一步出现了什么问题，怎么处理的）
```

---

## 汇总

三轮跑完后填：

| 步骤 | 平均耗时 | 最长耗时 | 三轮结果是否一致 |
|---|---:|---:|---|
| Content Agent 结构化 | | | |
| C001 推荐 | | | |
| C005 推荐 + NO_SEND | | | |
| C003 推荐 Before | | | |
| Quick Capture（张姐） | | | |
| C003 推荐 After | | | |
| Quick Capture（王阿姨） | | | |
| 今日运营摘要 | | | |

## 判定

进入正式演示的条件：

- [ ] 三轮的 SEND / NO_SEND 名单完全一致；
- [ ] 三轮结果都与 `tools/validate_demo_data.py --explain` 的输出一致；
- [ ] Quick Capture 三轮都在 15 秒内出草稿；
- [ ] 整场三轮都在 10 分钟内；
- [ ] Plan B 的 `Demo_After` 副本已备好；
- [ ] Plan C 的完整录屏已录好。

任何一项不达标，先修再演。
