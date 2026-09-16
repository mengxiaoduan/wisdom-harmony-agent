"""调度器：把 内容引擎 + 护栏 + 连接器 串成一次完整的运行。

run 一次 = 挑一个主题发一篇帖 + 巡查评论区回复一轮。
由 CLI 或 GitHub Actions 的 cron 驱动。
"""

import json
import time
from pathlib import Path

from . import config, content_engine, guardrails
from .connectors.github_discussions import GitHubDiscussions

OUTBOX = Path("outbox")


def _conn() -> GitHubDiscussions:
    cfg = config.load_config()
    if not cfg["repo"]:
        raise RuntimeError("未配置仓库：请设置 WHA_REPO=owner/name 或写入 config.json 的 repo 字段。")
    return GitHubDiscussions(config.load_token(), cfg["repo"], cfg["category"])


def _save_draft(name: str, content: dict) -> Path:
    OUTBOX.mkdir(exist_ok=True)
    path = OUTBOX / ("%s-%s.json" % (time.strftime("%Y%m%d-%H%M%S"), name))
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def step_post(auto_publish: bool = False) -> str:
    """生成并（可选）发布一篇帖子。返回动作说明。"""
    cfg = config.load_config()
    state = guardrails._load_state()
    idx = int(state.get("topic_index", 0))
    topic = content_engine.pick_topic(idx)

    post = content_engine.generate_post(topic, seed=idx)
    limiter = guardrails.RateLimiter(cfg["daily_post_limit"], "post")

    if not limiter.allow():
        return "今日发帖额度已用完（每日上限 %d），帖子暂存草稿箱。" % cfg["daily_post_limit"]

    if auto_publish:
        conn = _conn()
        d = conn.publish_post(post["title"], post["body"])
        limiter.record()
        s2 = guardrails._load_state()
        s2["topic_index"] = idx + 1
        s2["last_post_url"] = d.get("url")
        guardrails.save_state(s2)
        return "已发布：%s" % d.get("url")
    else:
        path = _save_draft("post-t%d" % idx, post)
        s2 = guardrails._load_state()
        s2["topic_index"] = idx + 1
        guardrails.save_state(s2)
        return "dry-run：帖子草稿已保存到 %s（加 --auto-post 才会真正发布）" % path


def step_reply(auto_publish: bool = False) -> str:
    """巡查评论区，为未回复的评论生成（可选发布）回复。"""
    cfg = config.load_config()
    conn = _conn()
    pending = conn.list_pending_comments()
    if not pending:
        return "评论区没有待回复的留言。"

    limiter = guardrails.RateLimiter(cfg["daily_reply_limit"], "reply")
    replied_ids = set(guardrails._load_state().get("replied_comment_ids", []))
    results = []

    for item in pending:
        if item["comment_id"] in replied_ids:
            continue
        if not limiter.allow():
            results.append("达到每日回复上限，其余已存草稿。")
            break
        r = content_engine.generate_reply(item["body"], seed=hash(item["comment_id"]) % 10**9)
        if auto_publish:
            c = conn.publish_reply(item["discussion_id"], r["body"])
            limiter.record()
            replied_ids.add(item["comment_id"])
            results.append("已回复 #%s 中 @%s：%s" % (item["discussion_number"], item["author"], c.get("url")))
        else:
            item["draft_reply"] = r["body"]
            item["reply_kind"] = r["kind"]
            _save_draft("reply-d%d-%s" % (item["discussion_number"], item["author"]), item)
            replied_ids.add(item["comment_id"])  # 草稿也不再重复生成
            results.append("dry-run：已为 #%s 中 @%s 的留言生成草稿" % (item["discussion_number"], item["author"]))

    s2 = guardrails._load_state()
    s2["replied_comment_ids"] = list(replied_ids)[-500:]  # 防无限增长
    guardrails.save_state(s2)
    return "\n".join(results)


def status() -> str:
    cfg = config.load_config()
    state = guardrails._load_state()
    today = time.strftime("%Y-%m-%d")
    posts_today = state.get("published", {}).get(today, {}).get("post", 0)
    replies_today = state.get("published", {}).get(today, {}).get("reply", 0)
    lines = [
        "仓库: %s" % (cfg["repo"] or "未配置"),
        "今日已发帖: %d / 上限 %d" % (posts_today, cfg["daily_post_limit"]),
        "今日已回复: %d / 上限 %d" % (replies_today, cfg["daily_reply_limit"]),
        "主题进度: 第 %d 篇（共 %d 个主题）" % (state.get("topic_index", 0), len(content_engine.load_topics())),
        "最近一篇: %s" % state.get("last_post_url", "（尚无）"),
        "强制署名: 每条内容必须包含「%s」" % "智和 Agent（AI）生成",
    ]
    return "\n".join(lines)
