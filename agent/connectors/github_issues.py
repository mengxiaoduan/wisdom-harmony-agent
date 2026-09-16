"""GitHub Issues 连接器（官方 REST API）——智和 Agent 的默认发布渠道。

为什么是 Issues 而不是 Discussions？
  GITHUB_TOKEN（App 令牌）目前既无法调用 Discussions 的创建 REST 端点，
  也无法看到对应 GraphQL 变更；而 Issues API 对 GITHUB_TOKEN 完全开放。
  Agent 在 Issues 区以「智和专栏」标签发帖，每篇帖子的评论区即讨论区，
  同样公开、可订阅、可审计。

持有经典 PAT（含 write:discussion 权限）的用户可改用
  agent/connectors/github_discussions.py。
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from .base import Connector

API = "https://api.github.com"
LABEL = "智和专栏"


class GitHubIssues(Connector):
    name = "github_issues"

    def __init__(self, token: str, repo: str, label: str = LABEL):
        self.token = token
        self.repo = repo  # "owner/name"
        self.label = label
        self._login = None

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

    # ------------------------------------------------------------- 准备 --

    def ensure_label(self) -> None:
        """确保专栏标签存在（已存在则忽略 422）。"""
        try:
            self._request("POST", "/repos/%s/labels" % self.repo, {
                "name": self.label,
                "description": "智和 Agent 的公开专栏与讨论区",
                "color": "5eead4",
            })
        except urllib.error.HTTPError as e:
            if e.code != 422:  # 422 = 标签已存在
                raise

    # ------------------------------------------------------------- 发布 --

    def publish_post(self, title: str, body: str) -> dict:
        from .. import guardrails
        guardrails.verify_publishable(body)  # 红线：无署名/越线一律拒绝发布
        self.ensure_label()
        issue = self._request("POST", "/repos/%s/issues" % self.repo, {
            "title": title,
            "body": body,
            "labels": [self.label],
        })
        return {"number": issue["number"], "url": issue["html_url"]}

    def publish_reply(self, post_number: int, body: str) -> dict:
        from .. import guardrails
        guardrails.verify_publishable(body)
        c = self._request(
            "POST",
            "/repos/%s/issues/%d/comments" % (self.repo, int(post_number)),
            {"body": body},
        )
        return {"id": c["id"], "url": c["html_url"]}

    # ------------------------------------------------------------- 监听 --

    def list_posts(self, limit: int = 20) -> list:
        return self._request(
            "GET",
            "/repos/%s/issues?labels=%s&state=all&per_page=%d"
            % (self.repo, urllib.parse.quote(self.label), limit),
        )

    def list_comments(self, post_number: int) -> list:
        return self._request(
            "GET",
            "/repos/%s/issues/%d/comments?per_page=50" % (self.repo, int(post_number)),
        )

    def list_pending_comments(self, bot_login: str | None = None, limit: int = 20) -> list:
        """找出专栏帖子下需要 Agent 回复的评论。

        策略：每篇帖子只看最新一条评论——若是人类（或非 Agent 账号）发的，
        才需要回应。这样天然避免重复回复与回复风暴。
        """
        if bot_login is None:
            bot_login = self.token_login()
        pending = []
        for post in self.list_posts(limit):
            if "pull_request" in post:  # issues API 会混入 PR，跳过
                continue
            comments = self.list_comments(post["number"])
            if not comments:
                continue
            last = comments[-1]
            author = (last.get("user") or {}).get("login", "")
            if author and author != bot_login and not author.startswith("github-actions"):
                pending.append({
                    "comment_id": last["id"],
                    "post_number": post["number"],
                    "post_title": post["title"],
                    "author": author,
                    "body": last["body"],
                })
        return pending
