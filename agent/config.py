"""配置加载：环境变量 > config.json > 默认值。"""

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEFAULTS = {
    "repo": "",                      # 形如 "mengxiaoduan/wisdom-harmony-agent"
    "connector": "issues",           # issues（默认，GITHUB_TOKEN 可用）| discussions（需 PAT）
    "category": "announcements",     # discussions 模式下的分类 slug
    "issue_label": "智和专栏",        # issues 模式下的专栏标签
    "daily_post_limit": 1,
    "daily_reply_limit": 10,
    "dry_run_default": True,         # 默认先审后发
    "max_replies_per_comment": 1,    # 对同一条评论最多回复一次
    "language": "zh-CN",
}


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    path = Path(os.environ.get("WHA_CONFIG", ROOT / "config.json"))
    if path.exists():
        try:
            cfg.update(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            pass

    # 环境变量覆盖
    cfg["repo"] = os.environ.get("WHA_REPO", cfg["repo"])
    cfg["connector"] = os.environ.get("WHA_CONNECTOR", cfg["connector"])
    cfg["category"] = os.environ.get("WHA_CATEGORY", cfg["category"])
    cfg["issue_label"] = os.environ.get("WHA_ISSUE_LABEL", cfg["issue_label"])
    cfg["dry_run"] = os.environ.get("WHA_DRY_RUN", str(cfg["dry_run_default"]).lower()) in ("1", "true", "yes")
    if os.environ.get("WHA_DAILY_LIMIT"):
        cfg["daily_post_limit"] = int(os.environ["WHA_DAILY_LIMIT"])
    return cfg


def load_token() -> str:
    """优先 GITHUB_TOKEN；否则尝试从 git credential manager 读取（仅本机使用）。"""
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        return tok.strip()
    import subprocess
    try:
        inp = "protocol=https\nhost=github.com\n\n"
        out = subprocess.run(
            ["git", "credential", "fill"], input=inp, capture_output=True,
            text=True, timeout=15,
        ).stdout
        for line in out.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    raise RuntimeError("未找到 GitHub 凭据：请设置 GITHUB_TOKEN 环境变量。")
