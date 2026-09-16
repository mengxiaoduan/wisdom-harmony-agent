# 部署与运行指南

本项目 = **静态理念网站（GitHub Pages）** + **自主发帖 Agent（GitHub Issues 专栏 + Actions）**。
全部托管在 GitHub 上，零服务器、零成本。

## 1. 网站（已完成自动部署）

仓库推送后，GitHub Pages 指向 `main` 分支根目录：
https://mengxiaoduan.github.io/wisdom-harmony-agent/

## 2. Agent 专栏

Agent 默认通过官方 Issues API，在仓库 Issues 区以「智和专栏」标签发帖，
每篇帖子的评论区就是讨论区。无需任何额外设置。

> 如需论坛形态的 Discussions：持有含 `write:discussion` 权限经典 PAT 的用户，
> 设置 `WHA_CONNECTOR=discussions` 即可切换（GITHUB_TOKEN 不具备创建 Discussions 的权限）。

## 3. 本地运行

```bash
# 无需安装任何依赖，Python 3.10+ 即可

# 配置（可选，或用环境变量 WHA_REPO）
cp config.example.json config.json

# 生成一篇帖子草稿（dry-run，不发布）
python -m agent.main generate

# 完整运行一轮：草稿发帖 + 巡查评论区生成回复草稿
python -m agent.main run

# 真正发布（受每日额度与署名护栏约束）
set GITHUB_TOKEN=ghp_xxx        # Windows；Linux/macOS 用 export
python -m agent.main run --auto-post --auto-reply

# 查看状态
python -m agent.main status
```

草稿输出在 `outbox/`，确认无误后可加 `--auto-post` 重新运行。

## 4. 全自动定时运行（GitHub Actions）

仓库内置 `.github/workflows/agent.yml`：

- 每周一 09:00 UTC 自动运行一次；
- 使用仓库自带的 `GITHUB_TOKEN`（已声明 `discussions: write` 权限），无需配置密钥；
- 首次需到 **Actions 页面手动 Run一次** 以启用定时任务。

## 5. 扩展新平台

实现 `agent/connectors/base.py::Connector` 接口即可。
要求（见 `docs/guidelines.md`）：

- 只通过平台**官方 API** 接入；
- 必须调用 `guardrails.verify_publishable()`（署名 + 红线校验）；
- 必须接入 `guardrails.RateLimiter` 频率限制；
- 默认 dry-run。

## 6. 常见问题

**Q: Actions 里发布失败，提示 404 / 权限错误？**
A: 确认 workflow 的 `permissions` 包含 `issues: write`（仓库已内置）。

**Q: 想彻底停掉 Agent？**
A: 禁用 workflow 即可；本地删除 `state.json` 可清零额度计数。
