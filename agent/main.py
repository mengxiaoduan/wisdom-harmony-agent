"""智和 Agent 命令行入口。

用法示例：
  python -m agent.main generate                 # 生成一篇帖子草稿（不发布）
  python -m agent.main run                      # 生成帖子草稿 + 巡查评论区
  python -m agent.main run --auto-post --auto-reply   # 真正发布（受护栏约束）
  python -m agent.main status                   # 查看运行状态与额度
"""

import argparse
import json
import sys

from . import content_engine, scheduler


def main(argv=None):
    p = argparse.ArgumentParser(prog="wisdom-harmony-agent", description="智和 · WisHarmony Agent")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="生成一篇帖子草稿（不发布）")
    g.add_argument("--topic-index", type=int, default=None, help="指定主题序号")

    r = sub.add_parser("reply", help="为一条评论生成回复草稿（不发布）")
    r.add_argument("--comment", required=True, help="评论原文")

    run = sub.add_parser("run", help="运行一轮：发帖 + 回复巡查")
    run.add_argument("--auto-post", action="store_true", help="允许真正发布帖子（仍受每日上限约束）")
    run.add_argument("--auto-reply", action="store_true", help="允许真正发布回复")

    sub.add_parser("status", help="查看状态与今日额度")

    args = p.parse_args(argv)

    if args.cmd == "generate":
        idx = args.topic_index
        if idx is None:
            idx = int(scheduler.guardrails._load_state().get("topic_index", 0))
        topic = content_engine.pick_topic(idx)
        post = content_engine.generate_post(topic, seed=idx)
        print(json.dumps(post, ensure_ascii=False, indent=2))

    elif args.cmd == "reply":
        r = content_engine.generate_reply(args.comment)
        print("识别类型: %s" % r["kind"])
        print("-" * 40)
        print(r["body"])

    elif args.cmd == "run":
        print("[发帖]", scheduler.step_post(auto_publish=args.auto_post))
        print()
        try:
            print("[回复]", scheduler.step_reply(auto_publish=args.auto_reply))
        except Exception as e:
            print("[回复] 跳过：%s" % e)

    elif args.cmd == "status":
        print(scheduler.status())


if __name__ == "__main__":
    main(sys.argv[1:])
