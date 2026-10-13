#!/usr/bin/env python3
"""
横纵分析法报告 Markdown → PDF

用法:
  python md_to_pdf.py input.md output.pdf [--title "..."] [--author "玉笛百科"]

依赖: pip install weasyprint markdown
中文乱码根因：必须把本机真实存在的 CJK 字体写入 @font-face，不能依赖 Droid Sans Fallback。
"""

from __future__ import annotations

import argparse
import html as html_lib
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.request import urlopen

import markdown

SCRIPT_DIR = Path(__file__).resolve().parent
BUNDLED_FONT_DIR = SCRIPT_DIR / "fonts"

NOTO_SC_URL = (
    "https://cdn.jsdelivr.net/gh/notofonts/noto-cjk@main/"
    "Sans/SubsetOTF/SC/NotoSansSC-Regular.otf"
)

CJK_FONT_CANDIDATES = [
    BUNDLED_FONT_DIR / "NotoSansSC-Regular.otf",
    BUNDLED_FONT_DIR / "NotoSansSC-Regular.ttf",
    Path("/usr/local/share/fonts/cjk/NotoSansSC-Regular.otf"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf"),
    Path("/usr/share/fonts/truetype/noto/NotoSansSC-Regular.otf"),
    Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
    Path("/usr/share/fonts/truetype/arphic/uming.ttc"),
    Path("/System/Library/Fonts/PingFang.ttc"),
    Path("/System/Library/Fonts/STHeiti Light.ttc"),
    Path("/Library/Fonts/Arial Unicode.ttf"),
    Path("C:/Windows/Fonts/msyh.ttc"),
    Path("C:/Windows/Fonts/msyhbd.ttc"),
    Path("C:/Windows/Fonts/simhei.ttf"),
    Path("C:/Windows/Fonts/simsun.ttc"),
    Path("C:/Windows/Fonts/NotoSansSC-Regular.otf"),
]

LATIN_FONT_CANDIDATES = [
    Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/TTF/DejaVuSans.ttf"),
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
]

MONO_FONT_CANDIDATES = [
    Path("/usr/share/fonts/dejavu/DejaVuSansMono.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
    Path("C:/Windows/Fonts/consola.ttf"),
    Path("/System/Library/Fonts/Supplemental/Courier New.ttf"),
]

EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U00002600-\U000026FF"
    "\U0000FE0F"
    "\U0000200D"
    "]+"
)

META_KEYS = (
    "研究时间",
    "完成日期",
    "所属领域",
    "研究对象类型",
    "研究对象",
    "研究员",
    "研究方法",
    "方法论来源",
)


def path_to_css_url(path: Path) -> str:
    return path.resolve().as_uri()


def font_format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".otf":
        return "opentype"
    if suffix == ".ttc":
        return "collection"
    return "truetype"


def first_existing(paths) -> Path | None:
    for path in paths:
        try:
            if path.is_file() and path.stat().st_size > 1024:
                return path
        except OSError:
            continue
    return None


def fonts_from_fc_list() -> list[Path]:
    try:
        out = subprocess.check_output(
            ["fc-list", ":lang=zh", "file"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    found = []
    for line in out.splitlines():
        raw = line.split(":")[0].strip()
        if raw:
            found.append(Path(raw))
    return found


def download_noto_sc() -> Path | None:
    BUNDLED_FONT_DIR.mkdir(parents=True, exist_ok=True)
    dest = BUNDLED_FONT_DIR / "NotoSansSC-Regular.otf"
    if dest.is_file() and dest.stat().st_size > 1024:
        return dest
    print("[..] 未发现中文字体，正在下载 Noto Sans SC …")
    try:
        with urlopen(NOTO_SC_URL, timeout=60) as resp:
            dest.write_bytes(resp.read())
        if dest.stat().st_size > 1024:
            print(f"[OK] 字体已保存: {dest}")
            return dest
    except Exception as exc:
        if dest.exists():
            dest.unlink(missing_ok=True)
        print(f"[WARN] 下载中文字体失败: {exc}", file=sys.stderr)
    return None


def resolve_cjk_font() -> Path:
    found = first_existing(CJK_FONT_CANDIDATES) or first_existing(fonts_from_fc_list())
    if found:
        return found
    downloaded = download_noto_sc()
    if downloaded:
        return downloaded
    raise SystemExit(
        "未找到中文字体，PDF 会出现乱码。请安装 Noto Sans SC / 微软雅黑 / PingFang，\n"
        f"或把字体文件放到: {BUNDLED_FONT_DIR}"
    )


def build_font_css(cjk_font: Path) -> str:
    latin = first_existing(LATIN_FONT_CANDIDATES)
    mono = first_existing(MONO_FONT_CANDIDATES)
    chunks = [
        f"""
@font-face {{
    font-family: "JadeCJK";
    src: url("{path_to_css_url(cjk_font)}") format("{font_format(cjk_font)}");
    font-weight: 100 900;
    font-style: normal;
    font-display: swap;
}}
"""
    ]
    if latin:
        chunks.append(
            f"""
@font-face {{
    font-family: "JadeLatin";
    src: url("{path_to_css_url(latin)}") format("{font_format(latin)}");
    font-weight: 400;
    font-style: normal;
}}
"""
        )
    if mono:
        chunks.append(
            f"""
@font-face {{
    font-family: "JadeMono";
    src: url("{path_to_css_url(mono)}") format("{font_format(mono)}");
    font-weight: 400;
    font-style: normal;
}}
"""
        )
    return "\n".join(chunks)


REPORT_CSS = """
:root {
    --ink: #12263a;
    --jade: #1b7a62;
    --jade-deep: #145c4a;
    --gold: #c4a35a;
    --paper: #fbf8f2;
    --muted: #5c6b73;
    --rule: #d7cfc2;
    --card: #f3eee4;
}

html { font-size: 10.5pt; }

@page {
    size: A4;
    margin: 22mm 18mm 20mm 18mm;

    @top-left {
        content: "玉笛百科";
        font-family: "JadeCJK", "JadeLatin", sans-serif;
        font-size: 8pt;
        color: #8a969e;
        letter-spacing: 0.12em;
        padding-bottom: 3mm;
        border-bottom: 0.4pt solid #e6dfd2;
    }
    @top-right {
        content: "HEADER_TEXT";
        font-family: "JadeCJK", "JadeLatin", sans-serif;
        font-size: 8pt;
        color: #8a969e;
        padding-bottom: 3mm;
        border-bottom: 0.4pt solid #e6dfd2;
    }
    @bottom-left {
        content: "横纵分析法深度研究报告";
        font-family: "JadeCJK", "JadeLatin", sans-serif;
        font-size: 8pt;
        color: #8a969e;
        padding-top: 3mm;
        border-top: 0.6pt solid #1b7a62;
    }
    @bottom-right {
        content: "第 " counter(page) " 页";
        font-family: "JadeCJK", "JadeLatin", sans-serif;
        font-size: 8pt;
        color: #8a969e;
        padding-top: 3mm;
        border-top: 0.6pt solid #1b7a62;
    }
}

@page :first {
    margin: 0;
    @top-left { content: none; border: none; }
    @top-right { content: none; border: none; }
    @bottom-left { content: none; border: none; }
    @bottom-right { content: none; border: none; }
}

* { box-sizing: border-box; }

body {
    font-family: "JadeCJK", "JadeLatin", "Noto Sans SC", "Microsoft YaHei", "PingFang SC", sans-serif;
    color: var(--ink);
    line-height: 1.78;
    font-size: 10.5pt;
    text-align: left;
    background: #fff;
}

.cover {
    page-break-after: always;
    min-height: 297mm;
    padding: 28mm 22mm 24mm 22mm;
    background: linear-gradient(165deg, #102033 0%, #16324c 58%, #145c4a 100%);
    color: #f7f1e6;
}

.cover-brand {
    font-size: 11pt;
    letter-spacing: 0.42em;
    color: #c4a35a;
    font-weight: 600;
}

.cover-kicker {
    margin-top: 4mm;
    font-size: 9.5pt;
    letter-spacing: 0.18em;
    color: rgba(247, 241, 230, 0.72);
}

.cover-rule {
    width: 28mm;
    height: 0;
    border: none;
    border-top: 1.6pt solid #c4a35a;
    margin: 14mm 0 10mm 0;
}

.cover h1 {
    font-size: 26pt;
    line-height: 1.35;
    margin: 0 0 8mm 0;
    color: #fff;
    font-weight: 700;
    border: none;
    page-break-before: avoid;
    padding: 0;
}

.cover-sub {
    font-size: 13pt;
    color: rgba(247, 241, 230, 0.84);
    margin-bottom: 14mm;
}

.cover-meta {
    display: block;
    font-size: 10pt;
    line-height: 1.9;
    color: rgba(247, 241, 230, 0.88);
}

.cover-meta span {
    display: block;
}

.cover-foot {
    margin-top: 28mm;
    font-size: 9pt;
    letter-spacing: 0.16em;
    color: rgba(247, 241, 230, 0.55);
}

.toc {
    page-break-after: always;
}

.toc h1 {
    page-break-before: avoid;
    margin-top: 0;
}

.toc-list {
    list-style: none;
    padding: 0;
    margin: 6mm 0 0 0;
}

.toc-list li {
    margin: 0;
    padding: 2.2mm 0;
    border-bottom: 0.3pt dotted var(--rule);
    font-size: 11pt;
}

.toc-list a {
    color: var(--ink);
    text-decoration: none;
}

.toc-list a::after {
    content: leader(".") target-counter(attr(href), page);
    color: var(--muted);
    font-size: 9.5pt;
}

.toc-h3 {
    padding-left: 7mm;
    font-size: 10pt;
    color: var(--muted);
}

h1 {
    font-size: 18pt;
    color: var(--ink);
    margin: 12mm 0 6mm 0;
    padding: 0 0 3mm 0;
    border-bottom: 1.6pt solid var(--jade);
    page-break-before: always;
    page-break-after: avoid;
    font-weight: 700;
    line-height: 1.35;
}

h2 {
    font-size: 13.5pt;
    color: var(--jade-deep);
    margin: 9mm 0 4mm 0;
    padding-left: 3.5mm;
    border-left: 2.4pt solid var(--jade);
    page-break-after: avoid;
    font-weight: 700;
    line-height: 1.4;
}

h3 {
    font-size: 11.5pt;
    color: #1f4e79;
    margin: 6mm 0 2.5mm 0;
    page-break-after: avoid;
    font-weight: 700;
}

h4 {
    font-size: 10.8pt;
    color: #5b2c6f;
    margin: 4.5mm 0 2mm 0;
    page-break-after: avoid;
}

p {
    margin: 2mm 0;
    orphans: 3;
    widows: 3;
}

blockquote {
    margin: 4.5mm 0;
    padding: 3.5mm 4.5mm 3.5mm 6mm;
    background: var(--card);
    border-left: 2.6pt solid var(--jade);
    color: #3d4f5f;
    font-size: 10pt;
}

blockquote p { margin: 1mm 0; }

strong, b {
    font-weight: 700;
    color: #0f1c28;
}

em { color: #3d4f5f; }

code {
    font-family: "JadeMono", "DejaVu Sans Mono", "Courier New", monospace;
    background: #f4efe6;
    color: #9b2c2c;
    padding: 0 1.2mm;
    font-size: 9.3pt;
}

pre {
    background: #12263a;
    color: #eef3f6;
    padding: 4mm;
    font-size: 8.8pt;
    line-height: 1.5;
    white-space: pre-wrap;
}

pre code {
    background: none;
    color: inherit;
    padding: 0;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 4.5mm 0;
    font-size: 9.4pt;
    page-break-inside: avoid;
}

thead th {
    background: #12263a;
    color: #f7f1e6;
    padding: 2.6mm 3mm;
    text-align: left;
    font-weight: 700;
}

tbody td {
    padding: 2.2mm 3mm;
    border-bottom: 0.4pt solid var(--rule);
    vertical-align: top;
}

tbody tr:nth-child(even) { background: #f7f3eb; }

hr {
    border: none;
    border-top: 0.4pt solid var(--rule);
    margin: 6mm 0;
}

ul, ol {
    margin: 2mm 0 3mm 0;
    padding-left: 7mm;
}

li { margin-bottom: 1.1mm; }

a { color: #1f4e79; text-decoration: none; }

img { max-width: 100%; }

.summary {
    background: var(--paper);
    border: 0.6pt solid var(--rule);
    padding: 5mm 6mm;
    margin: 0 0 8mm 0;
}

.summary h2 {
    border: none;
    padding: 0;
    margin-top: 0;
    color: var(--ink);
}

.sources {
    font-size: 9.5pt;
    color: #3d4f5f;
}
"""


def slugify(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = html_lib.unescape(text).strip()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^\w\u4e00-\u9fff\-]+", "", text)
    return text[:48] or "section"


def extract_meta(md_text: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    for raw in md_text.splitlines()[:40]:
        line = raw.strip().lstrip(">").strip()
        if not line:
            continue
        parts = re.split(r"\s*\|\s*", line)
        chunks = parts if len(parts) > 1 else [line]
        for chunk in chunks:
            for key in META_KEYS:
                if chunk.startswith(key):
                    value = re.sub(rf"^\**{re.escape(key)}\**\s*[:：]\s*", "", chunk).strip()
                    value = value.strip("*").strip()
                    if value:
                        meta[key] = value
    return meta


def strip_first_h1(md_text: str) -> tuple[str, str]:
    match = re.search(r"^#\s+(.+?)\s*$", md_text, re.M)
    title = match.group(1).strip() if match else ""
    if match:
        md_text = md_text[: match.start()] + md_text[match.end() :].lstrip("\n")
    return title, md_text


def strip_leading_meta_block(md_text: str) -> str:
    lines = md_text.splitlines()
    i = 0
    consumed = False
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            i += 1
            continue
        if stripped in {"---", "***"}:
            if consumed:
                i += 1
            break
        if stripped.startswith(">"):
            inner = stripped.lstrip(">").strip()
            if any(k in inner for k in META_KEYS) or consumed:
                consumed = True
                i += 1
                continue
        break
    return "\n".join(lines[i:]).lstrip("\n") if consumed else md_text


def wrap_special_sections(body: str) -> str:
    body = re.sub(
        r"<h2>([^<]*(?:核心结论|速览)[^<]*)</h2>(.*?)(?=<h[1-2]\b|$)",
        r'<section class="summary"><h2>\1</h2>\2</section>',
        body,
        count=1,
        flags=re.S,
    )
    body = re.sub(
        r"<h2>([^<]*(?:信息来源|参考资料)[^<]*)</h2>",
        r'<h2 class="sources-h">\1</h2>',
        body,
        count=1,
    )
    return body


def collect_toc(body: str) -> tuple[str, str]:
    toc_items = []

    def replacer(match: re.Match) -> str:
        level = match.group(1)
        attrs = match.group(2) or ""
        inner = match.group(3)
        if re.search(r"目录", inner):
            return match.group(0)
        heading_id = slugify(inner) + f"-{len(toc_items)+1}"
        toc_items.append((level, inner, heading_id))
        attrs = re.sub(r'\s+id="[^"]*"', "", attrs)
        return f'<h{level}{attrs} id="{heading_id}">{inner}</h{level}>'

    body = re.sub(r"<h([1-3])([^>]*)>(.*?)</h\1>", replacer, body, flags=re.S)
    if not toc_items:
        return "", body

    lines = ['<nav class="toc">', "<h1>目录</h1>", '<ol class="toc-list">']
    for level, inner, heading_id in toc_items:
        cls = ' class="toc-h3"' if level == "3" else ""
        if level == "1" and len(toc_items) > 8:
            pass
        lines.append(
            f'<li{cls}><a href="#{heading_id}">{inner}</a></li>'
        )
    lines += ["</ol>", "</nav>"]
    return "\n".join(lines), body


def md_to_html(
    md_text: str,
    title: str = "横纵分析报告",
    author: str = "玉笛百科",
    subtitle: str = "横纵分析法深度研究报告",
    meta: dict[str, str] | None = None,
    cjk_font: Path | None = None,
) -> str:
    md_text = EMOJI_RE.sub("", md_text)
    extracted_title, body_md = strip_first_h1(md_text)
    if extracted_title and (not title or title == "横纵分析报告"):
        title = extracted_title
    meta = meta or extract_meta(md_text)
    body_md = strip_leading_meta_block(body_md)

    html_body = markdown.markdown(
        body_md,
        extensions=["tables", "fenced_code", "sane_lists", "nl2br", "smarty"],
        output_format="html5",
    )
    html_body = wrap_special_sections(html_body)
    toc_html, html_body = collect_toc(html_body)

    cjk_font = cjk_font or resolve_cjk_font()
    font_css = build_font_css(cjk_font)
    header_text = title.replace('"', "")
    if len(header_text) > 28:
        header_text = header_text[:28] + "…"
    css = REPORT_CSS.replace("HEADER_TEXT", html_lib.escape(header_text))

    meta_rows = []
    order = ["所属领域", "研究对象类型", "研究时间", "完成日期", "研究方法", "研究员"]
    seen = set()
    for key in order:
        if key in meta:
            meta_rows.append(f"<span>{html_lib.escape(key)}　{html_lib.escape(meta[key])}</span>")
            seen.add(key)
    if author and "研究员" not in seen:
        meta_rows.append(f"<span>研究员　{html_lib.escape(author)}</span>")

    cover = f"""
<section class="cover">
  <div class="cover-brand">玉笛百科 JADE FLUTE</div>
  <div class="cover-kicker">HORIZONTAL · VERTICAL ANALYSIS</div>
  <hr class="cover-rule">
  <h1>{html_lib.escape(title)}</h1>
  <div class="cover-sub">{html_lib.escape(subtitle)}</div>
  <div class="cover-meta">
    {''.join(meta_rows)}
  </div>
  <div class="cover-foot">ENCYCLOPEDIA REPORT</div>
</section>
"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{html_lib.escape(title)}</title>
<style>
{font_css}
{css}
</style>
</head>
<body>
{cover}
{toc_html}
<article class="report-body">
{html_body}
</article>
</body>
</html>
"""


def write_pdf_weasyprint(html: str, output: Path, base_url: Path) -> None:
    from weasyprint import HTML
    from weasyprint.text.fonts import FontConfiguration

    font_config = FontConfiguration()
    HTML(
        string=html,
        encoding="utf-8",
        base_url=str(base_url) + os.sep,
    ).write_pdf(str(output), font_config=font_config)


def write_pdf_playwright(html_path: Path, output: Path) -> None:
    from playwright.sync_api import sync_playwright

    uri = html_path.resolve().as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(uri, wait_until="load")
        page.pdf(
            path=str(output),
            format="A4",
            print_background=True,
            display_header_footer=False,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        )
        browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="横纵分析法报告 Markdown → PDF")
    parser.add_argument("input", help="输入 Markdown")
    parser.add_argument("output", help="输出 PDF")
    parser.add_argument("--title", default=None, help="报告标题")
    parser.add_argument("--author", default="玉笛百科", help="作者 / 研究员")
    parser.add_argument("--subtitle", default="横纵分析法深度研究报告")
    parser.add_argument(
        "--engine",
        choices=["weasyprint", "playwright", "auto"],
        default="weasyprint",
        help="PDF 引擎。weasyprint 为默认；auto 失败时回退 playwright",
    )
    args = parser.parse_args()

    src = Path(args.input)
    dest = Path(args.output)
    if not src.is_file():
        raise SystemExit(f"找不到输入文件: {src}")

    md_text = src.read_text(encoding="utf-8")
    cjk_font = resolve_cjk_font()
    print(f"[OK] 中文字体: {cjk_font}")

    html = md_to_html(
        md_text,
        title=args.title or "横纵分析报告",
        author=args.author,
        subtitle=args.subtitle,
        cjk_font=cjk_font,
    )

    dest.parent.mkdir(parents=True, exist_ok=True)
    html_path = dest.with_suffix(".html")
    html_path.write_text(html, encoding="utf-8")
    print(f"[OK] HTML: {html_path}")

    engines = [args.engine] if args.engine != "auto" else ["weasyprint", "playwright"]
    last_error: Exception | None = None
    for engine in engines:
        try:
            if engine == "weasyprint":
                write_pdf_weasyprint(html, dest, html_path.parent)
            else:
                write_pdf_playwright(html_path, dest)
            size_kb = dest.stat().st_size / 1024
            print(f"[OK] PDF ({engine}): {dest} ({size_kb:.1f} KB)")
            return
        except Exception as exc:
            last_error = exc
            print(f"[WARN] {engine} 失败: {exc}", file=sys.stderr)

    raise SystemExit(f"PDF 生成失败: {last_error}")


if __name__ == "__main__":
    main()
