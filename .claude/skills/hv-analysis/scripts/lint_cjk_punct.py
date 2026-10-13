#!/usr/bin/env python3
"""
检查横纵报告 Markdown 里的中英文标点混用。

中文句子用全角：，。（）：？！「」《》
半角 , . : ? ! ( ) 只留给英文、数字、代码、URL。

用法:
  python lint_cjk_punct.py report.md
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FULL_CLOSE = set("」』》）】")
FULL_OPEN = set("「『《（【")


def is_cjk(ch: str) -> bool:
    return bool(ch) and "\u4e00" <= ch <= "\u9fff"


def is_ascii_word(ch: str) -> bool:
    return bool(ch) and ch.isascii() and ch.isalpha()


def mask_exempt(text: str) -> str:
    """用空格盖住代码、URL、Markdown 链接目标，避免误报。"""

    def keep_newlines(match: re.Match) -> str:
        return re.sub(r"[^\n]", " ", match.group(0))

    text = re.sub(r"```[\s\S]*?```", keep_newlines, text)
    text = re.sub(r"`[^`\n]+`", keep_newlines, text)
    text = re.sub(r"https?://[^\s)]+", keep_newlines, text)
    text = re.sub(r"(?<=\])\([^)]+\)", keep_newlines, text)
    return text


def neighbor(line: str, i: int, delta: int) -> str:
    j = i + delta
    while 0 <= j < len(line) and line[j] in " \t":
        j += delta
    if 0 <= j < len(line):
        return line[j]
    return ""


def check_line(line: str) -> list[str]:
    hits: list[str] = []
    for i, ch in enumerate(line):
        left, right = neighbor(line, i, -1), neighbor(line, i, 1)
        if ch == ",":
            if left.isdigit() and right.isdigit():
                continue
            if is_ascii_word(left) and is_ascii_word(right):
                continue
            if is_cjk(left) or is_cjk(right) or left in FULL_CLOSE or right in FULL_OPEN:
                hits.append("中文语境误用半角逗号 `,`，应改成 `，`")
        elif ch == ":" and (is_cjk(left) or left in FULL_CLOSE):
            hits.append("中文后面误用半角冒号 `:`，应改成 `：`")
        elif ch == "?" and (is_cjk(left) or left in FULL_CLOSE):
            hits.append("中文后面误用半角问号 `?`，应改成 `？`")
        elif ch == "!" and (is_cjk(left) or left in FULL_CLOSE):
            hits.append("中文后面误用半角感叹号 `!`，应改成 `！`")
        elif ch == ";" and (is_cjk(left) or is_cjk(right)):
            hits.append("中文语境误用半角分号 `;`，应改成 `；`")
        elif ch == "(" and (is_cjk(left) or is_cjk(right)):
            hits.append("中文语境误用半角括号 `(`，应改成 `（`")
        elif ch == ")" and (is_cjk(left) or is_cjk(right)):
            hits.append("中文语境误用半角括号 `)`，应改成 `）`")

    mixed_open = re.search(r"（[^）\n]*\)", line)
    if mixed_open:
        hits.append("全角左括号配了半角右括号")
    mixed_close = re.search(r"\([^（\n]*）", line)
    if mixed_close:
        hits.append("半角左括号配了全角右括号")
    return hits


def lint(md_text: str) -> list[tuple[int, str, str]]:
    masked = mask_exempt(md_text)
    findings: list[tuple[int, str, str]] = []
    raw_lines = md_text.splitlines()
    for i, line in enumerate(masked.splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("<!--"):
            continue
        for message in check_line(line):
            snippet = raw_lines[i - 1].strip()
            if len(snippet) > 88:
                snippet = snippet[:88] + "…"
            findings.append((i, message, snippet))
    return findings


def format_report(path: Path, findings: list[tuple[int, str, str]]) -> str:
    if not findings:
        return f"[OK] 中英文标点: {path}"
    lines = [f"[FAIL] 中英文标点 {len(findings)} 处: {path}"]
    for i, message, snippet in findings[:80]:
        lines.append(f"  L{i}: {message}")
        lines.append(f"       {snippet}")
    if len(findings) > 80:
        lines.append(f"  … 其余 {len(findings) - 80} 处省略")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="检查横纵报告的中英文标点混用")
    parser.add_argument("input", nargs="+", help="Markdown 文件")
    args = parser.parse_args()

    failed = 0
    for raw in args.input:
        path = Path(raw)
        if not path.is_file():
            print(f"[ERR] 找不到文件: {path}", file=sys.stderr)
            failed += 1
            continue
        findings = lint(path.read_text(encoding="utf-8"))
        print(format_report(path, findings))
        if findings:
            failed += 1
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
