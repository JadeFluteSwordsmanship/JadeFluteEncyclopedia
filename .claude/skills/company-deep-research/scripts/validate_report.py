#!/usr/bin/env python3
"""用法：validate_report.py INPUT.json [--html OUTPUT.html]。"""
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

import argparse
from html.parser import HTMLParser
from pathlib import Path
from report_core import ReportError, load_report, render_html, validate_report


class OfflineHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.anchors = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        identity = values.get("id")
        if identity:
            if identity in self.ids:
                self.errors.append("重复 HTML ID：" + identity)
            self.ids.add(identity)
        href = values.get("href", "")
        if href.startswith("#"):
            self.anchors.append(href[1:])
        if tag in {"script", "img", "iframe", "link", "object", "embed", "video", "audio", "source", "base"}:
            if tag != "script" or "src" in values:
                self.errors.append("不允许外链资产或嵌入资源：" + tag)
        if any(k.lower().startswith("on") for k in values):
            self.errors.append("不允许 HTML 事件处理属性")
        if tag == "th" and values.get("scope") != "col":
            self.errors.append("表头缺少 scope=col")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)


def validate_html(report, content):
    validate_report(report)
    parser = OfflineHTMLParser()
    parser.feed(content)
    parser.close()
    for anchor in parser.anchors:
        if anchor not in parser.ids:
            parser.errors.append("目录或来源锚点不存在：" + anchor)
    if parser.errors:
        raise ReportError("HTML 校验失败：" + "；".join(parser.errors))
    # 同一份 JSON 必须对应当前资源的确定性输出，防止内容或内联脚本被替换。
    if content != render_html(report):
        raise ReportError("HTML 与当前 JSON／模板输出不一致，请重新生成；不接受手工 HTML 注入")


def main(argv=None):
    parser = argparse.ArgumentParser(description="校验 schema v1、来源引用与可选的离线 HTML 一致性")
    parser.add_argument("input", type=Path)
    parser.add_argument("--html", type=Path)
    args = parser.parse_args(argv)
    try:
        report = load_report(args.input)
        warnings = validate_report(report)
        if args.html:
            validate_html(report, args.html.read_text(encoding="utf-8"))
    except (ReportError, OSError, UnicodeError) as exc:
        print(f"校验失败：{exc}", file=sys.stderr)
        return 1
    print("校验通过：schema_version=1" + ("，HTML 离线资产及内容一致" if args.html else ""))
    for warning in warnings:
        print("提示：" + warning, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
