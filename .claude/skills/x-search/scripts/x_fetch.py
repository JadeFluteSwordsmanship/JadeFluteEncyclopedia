#!/usr/bin/env python3
"""Fetch X/Twitter posts via the public fxtwitter mirror.

x.com itself usually returns 403 from this runtime. This script does NOT
provide keyword firehose search; it fetches known tweet IDs / URLs.

Usage:
  python x_fetch.py tweet https://x.com/XFreeze/status/2109357638958153994
  python x_fetch.py tweet 2109357638958153994 2109300337203183940
  python x_fetch.py tweet --json <url-or-id>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request

API = "https://api.fxtwitter.com/status/{id}"
ID_RE = re.compile(r"(?:status/)?(\d{5,})")
UA = "JadeFluteEncyclopedia-x-search/1.0"


def parse_id(token: str) -> str:
    match = ID_RE.search(token.strip())
    if not match:
        raise ValueError(f"无法从 {token!r} 解析推文 ID")
    return match.group(1)


def fetch_tweet(tweet_id: str, timeout: float = 20.0) -> dict:
    url = API.format(id=tweet_id)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:400]
        raise SystemExit(f"HTTP {exc.code} fetching {url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"网络失败 {url}: {exc}") from exc
    if payload.get("code") != 200 or "tweet" not in payload:
        raise SystemExit(f"fxtwitter 未返回推文: {payload}")
    return payload["tweet"]


def fmt_author(author: dict) -> str:
    name = author.get("name") or ""
    screen = author.get("screen_name") or ""
    return f"{name} (@{screen})" if screen else name


def tweet_to_md(tweet: dict) -> str:
    lines = [
        f"### {fmt_author(tweet.get('author') or {})}",
        f"- 链接：{tweet.get('url') or ''}",
        f"- 时间：{tweet.get('created_at') or ''}",
        f"- 互动：views={tweet.get('views')} likes={tweet.get('likes')} "
        f"rt={tweet.get('retweets')} replies={tweet.get('replies')} bookmarks={tweet.get('bookmarks')}",
        "",
        tweet.get("text") or "",
    ]
    media = (tweet.get("media") or {}).get("all") or []
    if media:
        lines.append("")
        lines.append("媒体：")
        for item in media:
            lines.append(f"- {item.get('type')}: {item.get('url')}")
    quote = tweet.get("quote")
    if isinstance(quote, dict) and quote.get("text"):
        lines.extend(
            [
                "",
                f"> 引用 {fmt_author(quote.get('author') or {})} {quote.get('url') or ''}",
                ">",
            ]
        )
        for qline in (quote.get("text") or "").splitlines() or [""]:
            lines.append(f"> {qline}")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="按 ID/URL 读取 X 帖子（fxtwitter 镜像）")
    parser.add_argument("command", choices=["tweet"], help="目前只支持按帖子读取")
    parser.add_argument("targets", nargs="+", help="推文 URL 或数字 ID")
    parser.add_argument("--json", action="store_true", help="输出原始 tweet JSON 数组")
    args = parser.parse_args()

    tweets = []
    for token in args.targets:
        tweet_id = parse_id(token)
        tweets.append(fetch_tweet(tweet_id))

    if args.json:
        json.dump(tweets, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return

    print("# X 帖子")
    print()
    for i, tweet in enumerate(tweets):
        if i:
            print("---\n")
        print(tweet_to_md(tweet))


if __name__ == "__main__":
    main()
