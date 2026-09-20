# MVP-0 运营规则

## 核心原则

1. 宁可少发，不要乱发。
2. 无回复不等于负反馈。
3. 明确负反馈优先于 AI 推断。
4. 服务推荐优先由明确 Need 或 Service Intent 触发。
5. AI 只生成 Draft，运营确认后再执行居民触达。
6. 真实居民敏感数据不得提交到 GitHub。

## 数据纪律

- resident_id 创建后不重命名。
- Interactions 只追加；raw_note 不为演示还原而修改。
- 系统时间字段优先使用 SmartSheet 自带字段。
- Demo 数据可以重置，但应通过 Demo Before 备份重新开始。

## Demo 核心规则

- C003 Before：R003 张姐不进入亲子活动推荐名单。
- Quick Capture 后：R003 recent_interests 增加“亲子活动”。
- C003 After：R003 进入推荐名单，理由引用近期互动。
- C005：R009 陈叔必须 NO_SEND，原因是 avoid_topics=优惠促销。
- R014 王阿姨的上门助浴需求在当前 Services 中应无匹配。
