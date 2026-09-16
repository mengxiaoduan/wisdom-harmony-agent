"""GitHub Discussions 连接器（官方 REST API）。

智和 Agent 的"自家社区"：在自己仓库的 Discussions 里发帖与回复，
全部公开、可审计。使用 GITHUB_TOKEN 环境变量或本机 git 凭据。

注：部分 OAuth 令牌（如 Git Credential Manager 颁发的 gho_ 令牌）
在 GraphQL 中看不到 Discussions 变更，因此统一走 REST API。
"""

from __future__ import annotations

import json
import urllib.request

from .base import Connector

API = "https://api.github.com"


class GitHubDiscussions(Connector):
    name = "github_discussions"

    def __init__(self, token: str, repo: str, category_slug: str = "announcements"):
        self.token = token
        self.repo = repo  # "owner/name"
        self.category_slug = category_slug
        self._login = None
        self._categories = None

    # ------------------------------------------------------------- 底层 --

    def _request(self, method: str, path: str, body: dict | None = None) -> dict | list:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(
            API + path, data=data, method=method,
            headers={
                "Authorization": "Bearer %s" % self.token,
                "Accept": "application/vnd.github+json",
                "User-Agent": "wisdom-harmony-agent",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}

    def token_login(self) -> str:
        if self._login is None:
            self._login = self._request("GET", "/user")["login"]
        return self._login

    # ------------------------------------------------------------- 资源 --

    def category_id(self) -> int:
        """优先级：环境变量 WHA_CATEGORY_ID > REST 列表 > 报错。"""
        import os
        env_id = os.environ.get("WHA_CATEGORY_ID")
        if env_id:
            return int(env_id)
        try:
            cats = self._request(
                "GET", "/repos/%s/discussions/categories" % self.repo)
            for c in cats:
                if c["slug"] == self.category_slug:
                    return c["id"]
            if cats:
                return cats[0]["id"]
        except Exception as e:
            raise RuntimeError(
                "无法获取 Discussions 分类（REST 列表失败：%s）。"
                "请在环境中设置 WHA_CATEGORY_ID=<分类的数字ID>。" % e)
        raise RuntimeError("仓库没有任何 Discussions 分类。")

    # ------------------------------------------------------------- 发布 --

    def publish_post(self, title: str, body: str) -> dict:
        from .. import guardrails
        guardrails.verify_publishable(body)  # 红线：无署名/越线一律拒绝发布
        d = self._request("POST", "/repos/%s/discussions" % self.repo, {
            "title": title,
            "body": body,
            "category_id": self.category_id(),
        })
        return {"number": d["number"], "url": d["html_url"], "id": d["number"]}

    def publish_reply(self, discussion_number: int, body: str) -> dict:
        from .. import guardrails
        guardrails.verify_publishable(body)
        c = self._request(
            "POST",
            "/repos/%s/discussions/%d/comments" % (self.repo, int(discussion_number)),
            {"body": body},
        )
        return {"id": c["id"], "url": c["html_url"]}

    # ------------------------------------------------------------- 监听 --

    def list_discussions(self, limit: int = 20) -> list:
        return self._request(
            "GET",
            "/repos/%s/discussions?per_page=%d" % (self.repo, limit),
        )

    def list_comments(self, discussion_number: int) -> list:
        return self._request(
            "GET",
            "/repos/%s/discussions/%d/comments?per_page=50" % (self.repo, int(discussion_number)),
        )

    def list_pending_comments(self, bot_login: str | None = None, limit: int = 20) -> list:
        """找出尚未被 Agent 回复过的顶层评论。"""
        if bot_login is None:
            bot_login = self.token_login()
        pending = []
        for d in self.list_discussions(limit):
            for c in self.list_comments(d["number"]):
                author = (c.get("user") or {}).get("login", "")
                if author and author != bot_login and not author.startswith("github-actions"):
                    pending.append({
                        "comment_id": c["id"],
                        "discussion_number": d["number"],
                        "discussion_title": d["title"],
                        "author": author,
                        "body": c["body"],
                    })
        return pending
