"""GitHub Discussions 连接器（官方 GraphQL API）。

智和 Agent 的"自家社区"：在自己仓库的 Discussions 里发帖与回复，
全部公开、可审计。使用 GITHUB_TOKEN 环境变量或本机 git 凭据。
"""

from __future__ import annotations

import json
import urllib.request

from .base import Connector

GRAPHQL_URL = "https://api.github.com/graphql"


class GitHubDiscussions(Connector):
    name = "github_discussions"

    def __init__(self, token: str, repo: str, category_slug: str = "announcements"):
        self.token = token
        self.repo = repo  # "owner/name"
        self.category_slug = category_slug
        self._repo_id = None
        self._category_id = None

    # ------------------------------------------------------------- 底层 --

    def graphql(self, query: str, variables: dict | None = None) -> dict:
        payload = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
        req = urllib.request.Request(
            GRAPHQL_URL,
            data=payload,
            headers={
                "Authorization": "Bearer %s" % self.token,
                "Content-Type": "application/json",
                "User-Agent": "wisdom-harmony-agent",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("errors"):
            raise RuntimeError("GraphQL 错误: %s" % json.dumps(data["errors"], ensure_ascii=False))
        return data["data"]

    def token_login(self) -> str:
        q = 'query { viewer { login } }'
        return self.graphql(q)["viewer"]["login"]

    # ------------------------------------------------------------- 资源 --

    def repo_id(self) -> str:
        if self._repo_id:
            return self._repo_id
        owner, name = self.repo.split("/")
        q = '''
        query($owner:String!,$name:String!){
          repository(owner:$owner,name:$name){ id hasDiscussionsEnabled }
        }'''
        d = self.graphql(q, {"owner": owner, "name": name})["repository"]
        if not d["hasDiscussionsEnabled"]:
            raise RuntimeError("仓库未启用 Discussions，请先在仓库设置中开启。")
        self._repo_id = d["id"]
        return self._repo_id

    def category_id(self) -> str:
        if self._category_id:
            return self._category_id
        owner, name = self.repo.split("/")
        q = '''
        query($owner:String!,$name:String!){
          repository(owner:$owner,name:$name){
            discussionCategories(first:20){ nodes { id name slug } }
          }
        }'''
        nodes = self.graphql(q, {"owner": owner, "name": name})[
            "repository"]["discussionCategories"]["nodes"]
        for n in nodes:
            if n["slug"] == self.category_slug:
                self._category_id = n["id"]
                return self._category_id
        # 回退到第一个分类
        if nodes:
            self._category_id = nodes[0]["id"]
            return self._category_id
        raise RuntimeError("仓库没有任何 Discussions 分类。")

    # ------------------------------------------------------------- 发布 --

    def publish_post(self, title: str, body: str) -> dict:
        from .. import guardrails
        guardrails.verify_publishable(body)  # 红线：无署名/越线一律拒绝发布
        m = '''
        mutation($repoId:ID!,$catId:ID!,$title:String!,$body:String!){
          addDiscussionPost(input:{repositoryId:$repoId,categoryId:$catId,title:$title,body:$body}){
            discussion{ id number url }
          }
        }'''
        d = self.graphql(m, {
            "repoId": self.repo_id(), "catId": self.category_id(),
            "title": title, "body": body,
        })
        return d["addDiscussionPost"]["discussion"]

    def publish_reply(self, discussion_id: str, body: str) -> dict:
        from .. import guardrails
        guardrails.verify_publishable(body)
        m = '''
        mutation($discussionId:ID!,$body:String!){
          addDiscussionComment(input:{discussionId:$discussionId,body:$body}){
            comment{ id url }
          }
        }'''
        d = self.graphql(m, {"discussionId": discussion_id, "body": body})
        return d["addDiscussionComment"]["comment"]

    # ------------------------------------------------------------- 监听 --

    def list_discussions(self, limit: int = 20) -> list:
        owner, name = self.repo.split("/")
        q = '''
        query($owner:String!,$name:String!,$limit:Int!){
          repository(owner:$owner,name:$name){
            discussions(first:$limit,orderBy:{field:CREATED_AT,direction:DESC}){
              nodes{
                id number title author{ login }
                comments(first:30){
                  nodes{ id body author{ login } createdAt }
                }
              }
            }
          }
        }'''
        nodes = self.graphql(q, {"owner": owner, "name": name, "limit": limit})[
            "repository"]["discussions"]["nodes"]
        return nodes

    def list_pending_comments(self, bot_login: str | None = None, limit: int = 20) -> list:
        """找出尚未被 Agent 回复过的顶层评论。"""
        if bot_login is None:
            bot_login = self.token_login()
        pending = []
        for d in self.list_discussions(limit):
            for c in d["comments"]["nodes"]:
                author = (c.get("author") or {}).get("login", "")
                if author and author != bot_login and author != "github-actions[bot]":
                    pending.append({
                        "comment_id": c["id"],
                        "discussion_id": d["id"],
                        "discussion_number": d["number"],
                        "discussion_title": d["title"],
                        "author": author,
                        "body": c["body"],
                    })
        return pending
