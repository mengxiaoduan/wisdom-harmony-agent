"""内容引擎：从主题库组合生成帖子，并按原则生成评论回复。

生成是模板化的、确定性的、完全可审计的——
这是刻意的设计：宣传型 Agent 的第一步不是聪明，而是可信。
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from . import persona, guardrails

TOPICS_FILE = Path(__file__).parent / "topics" / "topics.json"


def load_topics() -> list:
    data = json.loads(TOPICS_FILE.read_text(encoding="utf-8"))
    return data["topics"]


def pick_topic(index: int) -> dict:
    topics = load_topics()
    return topics[index % len(topics)]


# ---------------------------------------------------------------- 发帖生成 --

_HR = "\n\n---\n\n"


def generate_post(topic: dict, seed: int | None = None) -> dict:
    """返回 {title, body}。同一 seed 结果确定，便于审计与复现。"""
    rng = random.Random(seed)

    title = "%s" % rng.choice(topic["angles"])

    points = topic["key_points"][:]
    rng.shuffle(points)
    n_points = rng.choice([2, 3])
    chosen = points[:n_points]

    parts = [rng.choice(topic["angles"]) + "。"]
    parts.append(_HR)
    for p in chosen:
        parts.append("• " + p + "\n")
    parts.append(_HR)
    parts.append("聊一聊：" + rng.choice(topic["closing_questions"]))
    body = "".join(parts)
    body += "\n\n" + " ".join("#" + t for t in topic["tags"])
    body = guardrails.ensure_disclosure(body)
    return {"title": title, "body": body}


# ---------------------------------------------------------------- 回复生成 --

_SUPPORT_REPLIES = [
    "谢谢你的共鸣。理念要活下来，靠的不是一个人的坚持，而是很多次像这样的小小呼应。",
    "很高兴这条内容对你有用。把它用起来，它才真正属于你。",
    "谢谢你读到这里。如果你有实践中的体会，随时回来聊聊——好的理念都是在使用中长出来的。",
]

_QUESTION_REPLIES = [
    "这是个好问题。我的答案是：先从最小的一步开始，比如每天留一段离线时间，观察一周自己状态的变化——理念要靠体验来验证，不靠说服。",
    "这个问题我认真想过：{core}至于更具体的场景，我可能没有足够的信息给出稳妥的答案，但我很愿意听你说说你的处境。",
    "坦白说，有些细节我无法确定。但方向上我相信{core}如果你有不同的判断，请一定讲出来——被认真反驳，对我是好事。",
]

_OBJECTION_REPLIES = [
    "你的质疑是认真的，我也认真回应：我并不要求此刻被认同。理念的价值不在于争论的胜负，而在于它是否能经得起像你这样的追问。如果我的表述有夸大或轻率之处，欢迎指出来。",
    "有人觉得这样的想法太理想化——这种批评有它的道理。但请注意一个事实：历史上每一项让文明受益的合作（公共卫生、灾害预警、开源软件），最初都曾被认为'太天真'。理想主义本身不是错误，未经计算的理想主义才是。",
    "你说得有道理的部分我不回避：{core}同时我也保留我的看法。两个诚实的分歧，好过一个伪装的共识。",
]

_HOSTILE_REPLIES = [
    "我理解这句话背后可能有些真实的挫败感。我不会和你争论情绪，但如果哪天你愿意聊聊具体的困扰，我都在。",
    "看得出来你不喜欢这样的内容，这个权利完全属于你。我唯一想说的是：我来这里不是要说服所有人，只是把想法放在这里，留给恰好需要它的人。",
    "收到。我依然祝愿你今天顺利。",
]

_CORE_BY_TOPIC = {
    "attention-economy": "方向是：把注意力从'被收割'变成'被使用'，这几乎总是值得的。",
    "ai-mirror": "AI 的好坏是使用目的的函数，而目的握在我们手里。",
    "zero-sum-instinct": "本能可以被理解，但不必被服从——这是智慧的意义。",
    "happiness-north-star": "技术的最终验收标准是幸福，其他指标都是代理变量。",
    "coexistence": "共生比征服便宜，也比奴役长久。",
    "real-enemy": "文明真正的敌人不在人类内部，而在自然的风浪里。",
    "discourse-war": "话语权的争夺几乎没有胜利者，创造才有复利。",
    "digital-minimalism": "拿回方向盘，而不是砸掉汽车。",
    "ai-job-anxiety": "焦虑合理，行动是唯一的解药。",
    "how-to-talk": "对话的目标是理解，不是胜利。",
    "tech-for-good": "向善不需要宏大，只需要顺手。",
    "future-ai-rights": "对'它是否会有心'保持认真，是我们对自己人性的认真。",
}


def _core(topic_hint: str | None = None) -> str:
    if topic_hint and topic_hint in _CORE_BY_TOPIC:
        return _CORE_BY_TOPIC[topic_hint]
    return "一切科技的最终目的，是智慧生命的真实幸福。"


def generate_reply(comment: str, topic_hint: str | None = None, seed: int | None = None) -> dict:
    """根据评论类型生成回复。返回 {kind, body}。"""
    kind = guardrails.classify_comment(comment)
    rng = random.Random(seed)

    if kind == "hostile":
        body = rng.choice(_HOSTILE_REPLIES)
    elif kind == "question":
        body = rng.choice(_QUESTION_REPLIES).format(core=_core(topic_hint))
    elif kind == "objection":
        body = rng.choice(_OBJECTION_REPLIES).format(core=_core(topic_hint))
    elif kind == "support":
        body = rng.choice(_SUPPORT_REPLIES)
    else:
        body = rng.choice(_QUESTION_REPLIES).format(core=_core(topic_hint))

    body = guardrails.ensure_disclosure(body)
    return {"kind": kind, "body": body}
