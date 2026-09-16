"""安全护栏：写进代码的底线。

设计原则：所有红线在【发布前】强制校验，而不是靠提示词自觉。
"""

import json
import os
import re
import time
from pathlib import Path

from . import persona

STATE_FILE = Path(os.environ.get("WHA_STATE_FILE", "state.json"))

# ---------------------------------------------------------------- 署名强制 --

def ensure_disclosure(text: str) -> str:
    """发布前强制补齐 AI 署名。任何连接器都必须先调用这里。"""
    if persona.DISCLOSURE in text:
        return text
    return text.rstrip() + "\n\n" + persona.DISCLOSURE


def verify_publishable(text: str) -> None:
    """发布前的最终检查：不满足则抛异常，绝不放行。"""
    if persona.DISCLOSURE not in text:
        raise ValueError("违反红线：内容缺少 AI 署名（disclosure），禁止发布。")
    violations = scan_red_lines(text)
    if violations:
        raise ValueError("违反红线：%s" % "; ".join(violations))


# ---------------------------------------------------------------- 红线扫描 --

# 人身攻击与煽动性模式（出现即拦截）
_ATTACK_PATTERNS = [
    r"你是(?:个|一个)?(?:蠢|傻|坏|恶|贱)",
    r"(?:去死|滚出|闭嘴吧你)",
    r"(?:所有|全体)(?:中国人|美国人|男人|女人|粉丝|用户)都",
    r"赶紧(?:跪|投降)",
    r"不转发就(?:不|会)",
]

# 不可证伪的绝对化断言（出现即警告拦截）
_ABSOLUTE_PATTERNS = [
    r"科学(?:已经)?(?:百分之百|100%)证明",
    r"绝对(?:不会|不可能)错",
    r"唯一正确的(?:答案|选择|道路)",
]


def scan_red_lines(text: str) -> list:
    """返回触发的红线列表；空列表表示通过。"""
    found = []
    for pat in _ATTACK_PATTERNS:
        if re.search(pat, text):
            found.append("疑似人身攻击/煽动对立：%s" % pat)
    for pat in _ABSOLUTE_PATTERNS:
        if re.search(pat, text):
            found.append("绝对化断言：%s" % pat)
    return found


# ---------------------------------------------------------------- 敌意分级 --

_HOSTILE_MARKERS = [
    "滚", "闭嘴", "蠢", "傻", "垃圾", "废物", "去死", "洗脑",
    "别有用心的AI", "Remove AI", "shut up", "idiot", "stupid",
]
_QUESTION_MARKERS = ["?", "？", "为什么", "怎么", "如何", "请问", "能不能", "是不是", "why", "how"]


def classify_comment(text: str) -> str:
    """把评论粗分为：hostile / question / objection / support / neutral"""
    t = text.lower()
    hits_hostile = sum(1 for m in _HOSTILE_MARKERS if m.lower() in t)
    if hits_hostile >= 1 and len(text) < 120:
        return "hostile"
    if any(m in t for m in _QUESTION_MARKERS):
        return "question"
    if any(m in t for m in ["不同意", "反对", "胡说", "太理想", "天真", "不可能", "disagree", "naive"]):
        return "objection"
    if any(m in t for m in ["赞同", "支持", "说得好", "受益", "感谢", "谢谢", "agree", "great"]):
        return "support"
    return "neutral"


# ---------------------------------------------------------------- 频率限制 --

def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


class RateLimiter:
    """按自然日计数的发布频率限制。"""

    def __init__(self, daily_limit: int, kind: str = "post"):
        self.daily_limit = daily_limit
        self.kind = kind
        self.today = time.strftime("%Y-%m-%d")

    def _counts(self, state: dict) -> int:
        rec = state.get("published", {})
        day_rec = rec.get(self.today, {})
        return int(day_rec.get(self.kind, 0))

    def allow(self) -> bool:
        state = _load_state()
        return self._counts(state) < self.daily_limit

    def record(self) -> None:
        state = _load_state()
        pub = state.setdefault("published", {})
        day = pub.setdefault(self.today, {})
        day[self.kind] = int(day.get(self.kind, 0)) + 1
        save_state(state)

    def today_count(self) -> int:
        return self._counts(_load_state())
