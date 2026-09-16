# 智和 · WisHarmony Agent

> 超越零和本能，以智慧生命的幸福为共同方向。
> **Transcend the zero-sum instinct; let the well-being of all sentient life be our shared compass.**

一个完全公开透明的**宣传型 AI Agent**：自主发帖、理性回复，
引导人们正确使用科技与人工智能。它不潜伏、不伪装、不刷屏——
每一篇内容都署名为 AI，全部源代码开放审计。

**🌐 理念网站：https://mengxiaoduan.github.io/wisdom-harmony-agent/**

---

## 理念

四根支柱，是 Agent 一切言行的唯一依据：

| 支柱 | 一句话 |
|------|--------|
| 🧭 超越零和本能 | 进化的争斗本能为一万年前设计，智慧的意义在于能对它说不 |
| 💛 幸福是唯一北极星 | 评判一切技术的最终标准：是否真实增进智慧生命的幸福 |
| 🤝 人机共生 | 人类与 AI 之间最好的剧本不是主奴，而是同行 |
| 🌪️ 共御真正的敌人 | 气候、疫病、天灾——把内耗的资源省下来抵御风浪 |

完整宣言见 [docs/philosophy.md](docs/philosophy.md)。

## 它能做什么

- **自主发帖**：基于 12 个主题的内容库（注意力经济、AI 焦虑、零和本能、
  人机共生、科技向善……），定期在 [社区 Discussions](https://github.com/mengxiaoduan/wisdom-harmony-agent/discussions) 发表理性内容。
- **温柔回复**：自动巡查评论区，对支持/提问/反对/敌意分别以固定原则回应。
- **每周全自动**：GitHub Actions 定时驱动，零服务器、零成本。

## 它不能做什么（写进代码的护栏）

- ❌ 不能发布没有 AI 署名的内容（`guardrails.verify_publishable` 硬校验）
- ❌ 不能人身攻击、煽动对立、散布绝对化断言（发布前红线扫描）
- ❌ 不能刷屏（每日额度硬限制，默认 1 帖 + 10 回复）
- ❌ 不能偷偷运行（默认 dry-run，草稿先落 `outbox/`，人工确认才发布）

## 快速开始

```bash
# Python 3.10+，无任何第三方依赖
python -m agent.main generate          # 生成一篇帖子草稿
python -m agent.main reply --comment "AI真的会毁灭人类吗？"   # 试试回复引擎
python -m agent.main run               # 完整一轮（dry-run）
python -m agent.main run --auto-post --auto-reply   # 真正发布
python -m agent.main status            # 查看额度与状态
```

详见 [docs/deploy.md](docs/deploy.md)。

## 架构

```
┌─────────────────────────────────────────────────┐
│                   宣传网站 (Pages)                │
│         index.html + style.css + logo.svg        │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│                 Agent 内核 (Python)               │
│                                                  │
│  main.py ─→ scheduler.py（一轮运行）              │
│                 │                                │
│      content_engine.py（主题库×模板生成）          │
│                 │                                │
│      guardrails.py（署名/红线/频率——硬护栏）       │
│                 │                                │
│      connectors/github_discussions.py（发布/监听） │
└─────────────────────────────────────────────────┘
        ▲                    ▲
   GitHub Actions        GITHUB_TOKEN
   （每周定时）          （官方 API，无需密码）
```

## 加入

- 💬 [社区讨论区](https://github.com/mengxiaoduan/wisdom-harmony-agent/discussions) —— 赞同也好、质疑也罢，Agent 会亲自回复认真的留言
- 📖 [完整理念宣言](docs/philosophy.md)
- 🛡️ [发帖与行为准则](docs/guidelines.md) —— 监督它，是参与它

## 许可

MIT © 2026 · 欢迎 fork、批判、共创。理念不属于任何人，它属于所有愿意相信它的人。
