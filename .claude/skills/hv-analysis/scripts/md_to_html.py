#!/usr/bin/env python3
"""
横纵分析法报告 Markdown → 网页阅读版 HTML

用法:
  python md_to_html.py input.md output.html [--title "..."] [--author "玉笛百科"]

依赖: pip install markdown
视觉规范见 references/html-design.md；模板为 references/web-report.html。
"""

from __future__ import annotations

import argparse
import html as html_lib
import re
import sys
from pathlib import Path

import markdown

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = SCRIPT_DIR.parent / "references" / "web-report.html"

sys.path.insert(0, str(SCRIPT_DIR))
from md_to_pdf import (  # noqa: E402
    EMOJI_RE,
    extract_meta,
    strip_first_h1,
    strip_leading_meta_block,
)

TITLE_SPLIT = re.compile(r"\s*[：:]\s*", re.U)
SEC_ID_RE = re.compile(r"^sec-\d+$")
CJK_HREF_RE = re.compile(r'href="#([^"]*[^\x00-\x7f][^"]*)"')


def split_title(full: str) -> tuple[str, str]:
    parts = TITLE_SPLIT.split(full, maxsplit=1)
    if len(parts) == 2 and parts[0] and parts[1]:
        return parts[0].strip(), parts[1].strip()
    return full.strip(), ""


def word_count(md_text: str) -> int:
    text = re.sub(r"[>#*`|\[\]()_~]", " ", md_text)
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin = len(re.findall(r"[A-Za-z0-9]+", text))
    return cjk + latin


def reading_minutes(count: int) -> int:
    return max(1, round(count / 450))


def enrich_meta_from_tail(md_text: str, meta: dict[str, str]) -> dict[str, str]:
    tail = "\n".join(md_text.splitlines()[-30:])
    if "研究时间" not in meta and "完成日期" not in meta:
        match = re.search(r"\*\*?报告完成时间\*\*?[:：]\s*(.+)", tail)
        if match:
            meta["研究时间"] = match.group(1).strip().strip("*")
    return meta


def collect_toc(body: str) -> tuple[str, str]:
    toc_items: list[tuple[str, str, str]] = []

    def kind_mark(text: str) -> str:
        if re.search(r"纵向|诞生到当下", text):
            return "纵"
        if re.search(r"横向|竞争图谱", text):
            return "横"
        if re.search(r"交汇|洞察", text):
            return "汇"
        return ""

    def replacer(match: re.Match) -> str:
        level = match.group(1)
        attrs = match.group(2) or ""
        inner = match.group(3)
        if re.search(r"目录", inner):
            return match.group(0)
        heading_id = f"sec-{len(toc_items) + 1}"
        toc_items.append((level, inner, heading_id))
        attrs = re.sub(r'\s+id="[^"]*"', "", attrs)
        return f'<h{level}{attrs} id="{heading_id}">{inner}</h{level}>'

    body = re.sub(r"<h([1-3])([^>]*)>(.*?)</h\1>", replacer, body, flags=re.S)
    if not toc_items:
        return "", body

    lines = []
    for level, inner, heading_id in toc_items:
        mark = kind_mark(inner) if level in {"1", "2"} else ""
        kind = f'<span class="toc-kind" aria-hidden="true">{html_lib.escape(mark)}</span>' if mark else ""
        depth = "depth-2" if level == "2" else "depth-3"
        if level == "1":
            depth = "depth-2"
        label = html_lib.escape(re.sub(r"<[^>]+>", "", html_lib.unescape(inner)))
        lines.append(
            f'<li class="{depth}"><a href="#{heading_id}">{kind}{label}</a></li>'
        )
    return "\n".join(lines), body


def assert_ascii_toc(toc_html: str, body: str, full_html: str | None = None) -> None:
    """IM webview 不认中文 fragment。目录和标题必须是 ASCII sec-N。"""
    blob = full_html if full_html else (toc_html or "") + "\n" + (body or "")
    chinese = CJK_HREF_RE.findall(blob)
    if chinese:
        raise SystemExit(
            "HTML 目录禁止中文锚点（IM / 部分浏览器点了不跳）: "
            + ", ".join(f"#{item}" for item in chinese[:5])
        )
    hrefs = re.findall(r'<ol class="toc">[\s\S]*?</ol>', blob)
    href_ids = re.findall(r'<a href="#([^"]+)"', hrefs[0] if hrefs else (toc_html or ""))
    if toc_html or href_ids:
        if not href_ids:
            raise SystemExit("TOC 没有 href")
        for hid in href_ids:
            if not SEC_ID_RE.match(hid):
                raise SystemExit(f'TOC href 必须是 #sec-N，发现 #{hid}')
        if "sec-1" not in href_ids:
            raise SystemExit('TOC 缺少 href="#sec-1"')
    for hid in re.findall(r"<h[1-3][^>]*\sid=\"([^\"]+)\"", body):
        if not SEC_ID_RE.match(hid):
            raise SystemExit(f"标题 id 必须是 ASCII sec-N，发现: {hid}")
    if full_html:
        if "preventDefault" not in full_html or "scrollTo" not in full_html:
            raise SystemExit("网页模板 TOC 点击必须 preventDefault + scrollTo")


def autolink(body: str) -> str:
    parts = re.split(r"(<a\b[^>]*>.*?</a>)", body, flags=re.S)

    def repl(match: re.Match) -> str:
        url = match.group(1).rstrip(").,，。；;")
        return f'<a href="{html_lib.escape(url, quote=True)}">{html_lib.escape(url)}</a>'

    out = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            out.append(part)
        else:
            out.append(re.sub(r"(https?://[^\s<]+)", repl, part))
    return "".join(out)


def wrap_tables(body: str) -> str:
    return re.sub(r"<table\b[\s\S]*?</table>", lambda m: f'<div class="table-wrap">{m.group(0)}</div>', body)


def wrap_lead(body: str) -> str:
    def replacer(match: re.Match) -> str:
        attrs = match.group(1) or ""
        heading = match.group(2)
        rest = match.group(3)
        cls = "summary" if re.search(r"核心结论|速览", heading) else "lead-band"
        return f'<section class="{cls}"><h2{attrs}>{heading}</h2>{rest}</section>'

    return re.sub(
        r"<h2([^>]*)>([^<]*(?:核心结论|速览|一句话定义)[^<]*)</h2>(.*?)(?=<h[1-2]\b|$)",
        replacer,
        body,
        count=1,
        flags=re.S,
    )


def wrap_sources(body: str) -> str:
    def replacer(match: re.Match) -> str:
        attrs = match.group(1) or ""
        inner = match.group(2)
        if re.search(r"\bclass=", attrs):
            attrs = re.sub(r'class="([^"]*)"', r'class="\1 sources-h"', attrs, count=1)
        else:
            attrs = f' class="sources-h"{attrs}'
        return f"<h2{attrs}>{inner}</h2>"

    return re.sub(
        r"<h2([^>]*)>([^<]*(?:信息来源|参考资料)[^<]*)</h2>",
        replacer,
        body,
        count=1,
    )


def scenario_class(heading: str, index: int) -> str:
    if re.search(r"乐观|逆袭|重回|最好|上行", heading):
        return "scenario-up"
    if re.search(r"危险|失败|并购|退市|最差|下行|崩", heading):
        return "scenario-down"
    if re.search(r"可能|平平|基准|中性", heading):
        return "scenario-base"
    return ("scenario-up", "scenario-base", "scenario-down")[index % 3]


def wrap_scenarios(body: str) -> str:
    index = 0

    def replacer(match: re.Match) -> str:
        nonlocal index
        level, attrs, inner, rest = match.group(1), match.group(2) or "", match.group(3), match.group(4)
        cls = scenario_class(inner, index)
        index += 1
        return (
            f'<section class="scenario {cls}">'
            f"<h{level}{attrs}>{inner}</h{level}>{rest}</section>"
        )

    body = re.sub(
        r"<h([34])([^>]*)>([^<]*剧本[一二三123][^<]*|[^<]*(?:最可能|最危险|最乐观)[^<]*)</h\1>(.*?)(?=<h[1-4]\b|<section class=\"scenario|$)",
        replacer,
        body,
        flags=re.S,
    )

    def inline_replacer(match: re.Match) -> str:
        nonlocal index
        heading = re.sub(r"<[^>]+>", "", match.group(1))
        cls = scenario_class(heading, index)
        index += 1
        return (
            f'<section class="scenario {cls}">'
            f"<p><strong>{match.group(1)}</strong>{match.group(2)}</p>"
            f"{match.group(3)}</section>"
        )

    return re.sub(
        r"<p><strong>([^<]*剧本[\s\S]*?)</strong>([\s\S]*?)</p>(.*?)(?=<p><strong>[^<]*剧本|<h[1-4]\b|<section class=\"scenario|$)",
        inline_replacer,
        body,
        flags=re.S,
    )


def build_meta_html(meta: dict[str, str], author: str, count: int, minutes: int) -> str:
    chips: list[str] = []
    if meta.get("所属领域"):
        chips.append(meta["所属领域"])
    if meta.get("研究对象类型"):
        chips.append(meta["研究对象类型"])
    date = meta.get("研究时间") or meta.get("完成日期")
    if date:
        chips.append(date)
    chips.append(f"约 {count} 字")
    chips.append(f"阅读 {minutes} 分钟")
    researcher = meta.get("研究员") or author
    if researcher:
        chips.append(researcher)

    if not chips:
        return ""
    html_chips: list[str] = []
    if len(chips) >= 2:
        html_chips.append(
            f"<span>{html_lib.escape(chips[0])} · {html_lib.escape(chips[1])}</span>"
        )
        start = 2
    else:
        html_chips.append(f"<span>{html_lib.escape(chips[0])}</span>")
        start = 1
    for item in chips[start:]:
        html_chips.append(f"<span>{html_lib.escape(item)}</span>")
    return "".join(html_chips)


def md_to_reading_html(
    md_text: str,
    title: str = "横纵分析报告",
    author: str = "玉笛百科",
    subtitle: str = "",
    kicker: str = "横纵分析",
    page_suffix: str = "横纵分析报告",
    subtitle_fallback: str = "横纵分析法深度研究报告",
) -> str:
    md_text = EMOJI_RE.sub("", md_text)
    extracted_title, body_md = strip_first_h1(md_text)
    if extracted_title and (not title or title == "横纵分析报告"):
        title = extracted_title
    meta = enrich_meta_from_tail(md_text, extract_meta(md_text))
    body_md = strip_leading_meta_block(body_md)

    cover_title, cover_sub = split_title(title)
    if subtitle:
        cover_sub = subtitle
    elif not cover_sub:
        cover_sub = subtitle_fallback

    count = word_count(md_text)
    minutes = reading_minutes(count)

    html_body = markdown.markdown(
        body_md,
        extensions=["tables", "fenced_code", "sane_lists", "nl2br"],
        output_format="html5",
    )
    toc_html, html_body = collect_toc(html_body)
    html_body = wrap_lead(html_body)
    html_body = wrap_sources(html_body)
    html_body = wrap_scenarios(html_body)
    html_body = wrap_tables(html_body)
    html_body = autolink(html_body)
    assert_ascii_toc(toc_html, html_body)

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    replacements = {
        "PAGE_TITLE": html_lib.escape(f"{cover_title}{page_suffix}"),
        "TITLE": html_lib.escape(cover_title),
        "COVER_TITLE": html_lib.escape(cover_title),
        "SUBTITLE": html_lib.escape(cover_sub),
        "COVER_KICKER": html_lib.escape(kicker),
        "META_HTML": build_meta_html(meta, author, count, minutes),
        "TOC_HTML": toc_html,
        "BODY": html_body,
        "AUTHOR": html_lib.escape(meta.get("研究员") or author),
        "DATE": html_lib.escape(meta.get("研究时间") or meta.get("完成日期") or ""),
    }
    out = template
    for key, value in replacements.items():
        out = out.replace("{{" + key + "}}", value)
    leftover = re.findall(r"\{\{[A-Z0-9_]+\}\}", out)
    if leftover:
        raise SystemExit(f"模板占位符未替换: {leftover}")
    assert_ascii_toc(toc_html, html_body, full_html=out)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="横纵分析法报告 Markdown → 网页阅读版 HTML")
    parser.add_argument("input", help="输入 Markdown")
    parser.add_argument("output", help="输出 HTML")
    parser.add_argument("--title", default=None, help="封面主标题；默认取文首 H1")
    parser.add_argument("--subtitle", default="", help="封面副标题；默认从 H1 冒号后拆")
    parser.add_argument("--author", default="玉笛百科", help="作者 / 研究员")
    parser.add_argument("--kicker", default="横纵分析", help="封面左上角小标")
    parser.add_argument("--page-suffix", default="横纵分析报告", help="浏览器标题后缀")
    parser.add_argument(
        "--subtitle-fallback",
        default="横纵分析法深度研究报告",
        help="H1 拆不出副标题时的兜底",
    )
    args = parser.parse_args()

    src = Path(args.input)
    dest = Path(args.output)
    if not src.is_file():
        raise SystemExit(f"找不到输入文件: {src}")
    if not TEMPLATE_PATH.is_file():
        raise SystemExit(f"找不到网页模板: {TEMPLATE_PATH}")

    md_text = src.read_text(encoding="utf-8")
    try:
        from lint_cjk_punct import format_report, lint

        findings = lint(md_text)
        if findings:
            print(format_report(src, findings), file=sys.stderr)
            print("[WARN] 先改 Markdown 标点，再重新生成 HTML。", file=sys.stderr)
    except ImportError:
        pass

    html = md_to_reading_html(
        md_text,
        title=args.title or "横纵分析报告",
        author=args.author,
        subtitle=args.subtitle,
        kicker=args.kicker,
        page_suffix=args.page_suffix,
        subtitle_fallback=args.subtitle_fallback,
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html, encoding="utf-8")
    size_kb = dest.stat().st_size / 1024
    print(f"[OK] HTML: {dest} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
