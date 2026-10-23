#!/usr/bin/env python3
"""用法：render_report.py INPUT.json OUTPUT.html [--markdown OUTPUT.md]。"""
import sys

sys.dont_write_bytecode = True
# -I 下按脚本位置加载自己的资源，不依赖 cwd、HOME 或 PYTHONPATH。
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

import argparse
from pathlib import Path
from report_core import ReportError, load_report, render_html, render_markdown, validate_report


def main(argv=None):
    parser = argparse.ArgumentParser(description="生成单文件离线 HTML 研报，可选 Markdown companion")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args(argv)
    try:
        paths = [p.resolve() for p in [args.input, args.output, args.markdown] if p is not None]
        if len(set(paths)) != len(paths):
            raise ReportError("输入、HTML 和 Markdown 路径必须不同，不能覆盖输入")
        report = load_report(args.input)
        warnings = validate_report(report)
        output = render_html(report)
        markdown = render_markdown(report) if args.markdown else None
        for path in [args.output, args.markdown]:
            if path is not None and not path.parent.is_dir():
                raise ReportError(f"输出父目录不存在：{path.parent}")
        args.output.write_text(output, encoding="utf-8")
        if args.markdown:
            args.markdown.write_text(markdown, encoding="utf-8")
    except (ReportError, OSError, UnicodeError) as exc:
        print(f"生成失败：{exc}", file=sys.stderr)
        return 1
    print(f"已生成 HTML：{args.output}")
    if args.markdown:
        print(f"已生成 Markdown：{args.markdown}")
    for warning in warnings:
        print("提示：" + warning, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
