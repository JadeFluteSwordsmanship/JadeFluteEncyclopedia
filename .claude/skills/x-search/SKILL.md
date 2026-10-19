---
name: x-search
description: 读取 X/Twitter 帖子正文（按 URL 或 status ID）。x.com 直连在本运行时通常 403，默认用 fxtwitter 镜像。关键词火hose 搜索不可用，需先用 WebSearch 找到帖子链接再回取。用户给出 x.com/twitter.com 链接、推文 ID，或要求核验/引用某条推文时使用。
---

# X / Twitter 读取

本运行时**没有**原生 X 火hose，也没有 Bearer Token。不要假装能像 Grok 网页版那样按关键词实时搜全站。

已验证（2026-10-19）：

| 路径 | 结果 |
|------|------|
| `WebFetch` / curl `https://x.com/...` | 403 |
| `WebSearch site:x.com` | 经常空 |
| `https://api.fxtwitter.com/status/<id>` | **可用**，返回正文、作者、引用推、媒体、互动数 |
| 用户时间线 / 关键词搜索 API | 本环境不可用 |
| 独立 MCP | 无 X API 密钥，不建空 MCP |

## 按帖子读取

```bash
python .cursor/skills/x-search/scripts/x_fetch.py tweet <url-or-id> [<url-or-id> ...]
python .cursor/skills/x-search/scripts/x_fetch.py tweet --json <url-or-id>
```

依赖：Python 3 标准库，无需 pip。

## 关键词 / 舆情（两步，不要跳）

1. `WebSearch`：公司名 / ticker / 关键人士 + `twitter` 或 `X`。把结果里的 `status/<id>` 抠出来。
2. 用上面的脚本把 ID 拉成原文。二手转述（新闻里的「有人在 X 上说」）不能当一手。

找不到 ID 就写「X 原文暂缺」，不要编帖子。

## 交易研究里怎么用

读完 `.cursor/skills/trade-research/SKILL.md` 时，X 只承担**叙事和拥挤度**：

- CEO / 创始人原话、产品事故、发射与延期
- 散户在争哪条证伪、什么日期被反复提及
- 互动数暴增往往是拥挤信号，不是基本面证据

禁止：把点赞数当买入依据；把单条大 V 观点写成「市场共识」。
