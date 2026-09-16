"""连接器基类：所有发布渠道必须实现本接口，并遵守同样的护栏。"""


class Connector:
    name = "base"

    def publish_post(self, title: str, body: str) -> dict:
        raise NotImplementedError

    def publish_reply(self, parent_id: str, body: str) -> dict:
        raise NotImplementedError

    def list_pending_comments(self) -> list:
        """返回需要回复的评论：[{id, discussion_title, discussion_id, author, body, topic_hint}]"""
        raise NotImplementedError
