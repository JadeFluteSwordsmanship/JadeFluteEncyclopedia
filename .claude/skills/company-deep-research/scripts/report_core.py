"""仅依赖标准库的 schema v1 校验与离线研报渲染。"""
import sys

sys.dont_write_bytecode = True

import datetime as dt
import html
import json
import math
from pathlib import Path
import re
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
DISCLAIMER = "以上内容基于公开数据和量化分析，仅供参考，不构成投资建议。市场有风险，投资需谨慎。任何投资决策应结合个人风险承受能力、资金状况和投资目标独立判断，必要时咨询持牌专业机构。过往表现不预示未来收益。"
DEMO_NOTICE = "虚构公司／合成数据，仅验证模板，不用于投资"
DRAFT_NOTICE = "资料不足／研究骨架，尚未完成公司深度研究"
VERDICT_LABELS = ["盈利兑现", "逆境反转", "估值压缩", "预期提高"]
TONES = {"neutral", "primary", "risk", "positive"}
SOURCE_KINDS = {"primary", "secondary", "assumption", "demo"}
SOURCE_LABELS = {"primary": "一手来源", "secondary": "二手来源／需核实原文", "assumption": "假设／非已核实事实", "demo": "演示／合成数据"}
SOURCE_ID = re.compile(r"S[1-9][0-9]*\Z")


class ReportError(ValueError):
    pass


def fail(path, message):
    raise ReportError(f"{path}: {message}")


def text(value, path):
    if not isinstance(value, str) or not value.strip():
        fail(path, "必须为非空字符串")
    if any(ord(c) < 32 and c not in "\n\r\t" for c in value):
        fail(path, "不允许控制字符")


def obj(value, path, required, optional=()):
    if not isinstance(value, dict):
        fail(path, "必须为对象")
    missing = set(required) - value.keys()
    extra = value.keys() - set(required) - set(optional)
    if missing:
        fail(path, "缺少字段 " + ", ".join(sorted(missing)))
    if extra:
        fail(path, "未知字段 " + ", ".join(sorted(extra)))


def array(value, path, minimum=0, maximum=None):
    if not isinstance(value, list):
        fail(path, "必须为数组")
    if len(value) < minimum or (maximum is not None and len(value) > maximum):
        fail(path, f"数组长度应为 {minimum}..{maximum if maximum is not None else '不限'}")


def texts(value, path, minimum=1):
    array(value, path, minimum)
    for i, item in enumerate(value):
        text(item, f"{path}[{i}]")


def choice(value, path, allowed):
    if not isinstance(value, str) or value not in allowed:
        fail(path, "允许值：" + ", ".join(sorted(allowed)))


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except (OverflowError, ValueError):
        return False


def scalar(value, path, nullable=False):
    if nullable and value is None:
        return
    if isinstance(value, str):
        text(value, path)
    elif not number(value):
        fail(path, "必须为非空文本或有限数字；缺值仅允许 null，bool 不接受")


def date(value, path, timestamp=False):
    text(value, path)
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            dt.date.fromisoformat(value)
        elif timestamp and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)", value):
            dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            raise ValueError
    except ValueError:
        fail(path, "须为有效 ISO 日期" + ("或含时区的 ISO 时间戳" if timestamp else ""))


def safe_url(value, path, demo_allowed):
    text(value, path)
    if re.search(r"[\s\\<>\"'\x00-\x1f\x7f]", value):
        fail(path, "URL 包含不安全字符")
    # 百分号编码也不允许隐藏控制字符或反斜线。
    if re.search(r"%(?:0[0-9a-f]|1[0-9a-f]|7f|5c)", value, re.I):
        fail(path, "URL 包含编码的不安全字符")
    try:
        parts = urlsplit(value)
        port = parts.port
        host = parts.hostname
    except ValueError:
        fail(path, "无效 URL")
    if parts.username is not None or parts.password is not None:
        fail(path, "URL 不允许用户名或密码")
    allowed = {"http", "https", "demo"} if demo_allowed else {"http", "https"}
    if parts.scheme not in allowed or not host or not parts.netloc:
        fail(path, "只允许带主机的 http(s) URL；demo:// 仅用于演示源")
    if port is not None and not 1 <= port <= 65535:
        fail(path, "无效端口")


def references(value, path, ids, required=False):
    array(value, path, 1 if required else 0)
    seen = set()
    for ref in value:
        if not isinstance(ref, str) or not SOURCE_ID.fullmatch(ref) or ref not in ids:
            fail(path, f"引用不存在或格式无效：{ref!r}")
        if ref in seen:
            fail(path, f"重复引用：{ref}")
        seen.add(ref)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail("JSON", f"重复对象键：{key}")
        result[key] = value
    return result


def _constant(value):
    fail("JSON", f"不接受非标准数字 {value}")


def load_report(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_pairs, parse_constant=_constant)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReportError(f"无法读取 JSON：{exc}") from exc


def validate_report(report):
    required = "schema_version title company ticker market report_date subtitle as_of mode thesis summary verdicts kpis sections sources".split()
    obj(report, "report", required)
    if type(report["schema_version"]) is not int or report["schema_version"] != 1:
        fail("schema_version", "仅支持整数 1")
    for key in "title company ticker subtitle as_of thesis".split():
        text(report[key], key)
    choice(report["market"], "market", {"A股", "港股", "美股"})
    patterns = {"A股": r"[0-9]{6}", "港股": r"[0-9]{5}", "美股": r"[A-Z][A-Z0-9]*(?:[.-][A-Z0-9]+)*"}
    if len(report["ticker"]) > 16 or not re.fullmatch(patterns[report["market"]], report["ticker"]):
        fail("ticker", "A股须六位、港股须五位、美股须大写 ticker（允许 . 或 - 类别后缀）")
    date(report["report_date"], "report_date")
    choice(report["mode"], "mode", {"research", "demo", "draft"})
    texts(report["summary"], "summary")
    array(report["sources"], "sources", 0 if report["mode"] == "draft" else 1)
    ids = set()
    for i, source in enumerate(report["sources"]):
        path = f"sources[{i}]"
        obj(source, path, "id title url publisher published_at accessed_at kind".split())
        for key in "id title publisher".split():
            text(source[key], f"{path}.{key}")
        if not SOURCE_ID.fullmatch(source["id"]) or source["id"] in ids:
            fail(path + ".id", "来源 ID 必须唯一且形如 S1、S2")
        ids.add(source["id"])
        choice(source["kind"], path + ".kind", SOURCE_KINDS)
        if report["mode"] in {"research", "draft"} and source["kind"] == "demo":
            fail(path, f"{report['mode']} 禁止 demo 源；合成演示须使用 demo 模式")
        safe_url(source["url"], path + ".url", report["mode"] == "demo" and source["kind"] == "demo")
        date(source["published_at"], path + ".published_at", True)
        date(source["accessed_at"], path + ".accessed_at", True)
    if report["mode"] == "research":
        if not any(s["kind"] == "primary" for s in report["sources"]):
            fail("sources", "research 至少需要一个 primary 源；不机械要求八个")
    array(report["verdicts"], "verdicts", 4, 4)
    for i, item in enumerate(report["verdicts"]):
        path = f"verdicts[{i}]"
        obj(item, path, "label status detail tone".split())
        for key in "label status detail".split():
            text(item[key], path + "." + key)
        if item["label"] != VERDICT_LABELS[i]:
            fail(path + ".label", "四卡标签须依次为：" + "／".join(VERDICT_LABELS))
        choice(item["tone"], path + ".tone", TONES)
    array(report["kpis"], "kpis", 0, 6)
    for i, item in enumerate(report["kpis"]):
        path = f"kpis[{i}]"
        obj(item, path, "label value note sources period".split())
        for key in "label note period".split():
            text(item[key], path + "." + key)
        scalar(item["value"], path + ".value")
        references(item["sources"], path + ".sources", ids, True)
    array(report["sections"], "sections", 6, 7)
    for i, section in enumerate(report["sections"]):
        path = f"sections[{i}]"
        obj(section, path, "id title blocks".split())
        if section["id"] != f"q{i + 1}":
            fail(path + ".id", "章节须按 q1..qN 排列（N 为 6 或 7），ID 不重复；q7 仅可最后追加")
        text(section["title"], path + ".title")
        array(section["blocks"], path + ".blocks", 1)
        for j, block in enumerate(section["blocks"]):
            block_path = f"{path}.blocks[{j}]"
            validate_block(block, block_path, ids)
            if report["mode"] == "draft" and not ids and block["type"] != "paragraph":
                fail(block_path, "无来源 draft 仅允许定性资料缺口 paragraph，不得添加图表或其他组件")
    return report_warnings(report)


def validate_block(block, path, ids):
    if not isinstance(block, dict) or "type" not in block:
        fail(path, "block 必须有 type 字段")
    kind = block["type"]
    fields = {
        "paragraph": ("text", ""), "heading": ("text", ""),
        "callout": ("text tone", ""), "bullets": ("items", ""),
        "table": ("title columns rows", "period basis"),
        "chart": ("title categories series unit period", "kind"),
        "flow": ("title steps", ""), "cards": ("items", ""),
    }
    choice(kind, path + ".type", set(fields))
    required, optional = fields[kind]
    obj(block, path, ["type"] + required.split(), ["sources"] + optional.split())
    references(block.get("sources", []), path + ".sources", ids, kind == "chart")
    for key in "text title unit period basis".split():
        if key in block:
            text(block[key], path + "." + key)
    if "tone" in block:
        choice(block["tone"], path + ".tone", TONES)
    if kind == "bullets":
        texts(block["items"], path + ".items")
    elif kind == "flow":
        texts(block["steps"], path + ".steps")
    elif kind == "cards":
        array(block["items"], path + ".items", 1)
        for i, item in enumerate(block["items"]):
            p = f"{path}.items[{i}]"
            obj(item, p, "label text tone".split())
            text(item["label"], p + ".label")
            text(item["text"], p + ".text")
            choice(item["tone"], p + ".tone", TONES)
    elif kind == "table":
        texts(block["columns"], path + ".columns")
        array(block["rows"], path + ".rows", 1)
        numeric = False
        for i, row in enumerate(block["rows"]):
            p = f"{path}.rows[{i}]"
            array(row, p, len(block["columns"]), len(block["columns"]))
            for j, cell in enumerate(row):
                scalar(cell, f"{p}[{j}]", True)
                # 数字写成字符串也不能绕过来源／周期要求。
                numeric = numeric or number(cell) or cell is None or (isinstance(cell, str) and bool(re.search(r"\d|[零〇一二三四五六七八九十百千万亿两]", cell)))
        if numeric:
            references(block.get("sources", []), path + ".sources", ids, True)
            text(block.get("period"), path + ".period")
    elif kind == "chart":
        choice(block.get("kind", "line"), path + ".kind", {"line", "bar"})
        texts(block["categories"], path + ".categories")
        array(block["series"], path + ".series", 1)
        names = set()
        for i, series in enumerate(block["series"]):
            p = f"{path}.series[{i}]"
            # 单位只能在 chart 层声明；拒绝序列级混合量纲或双轴字段。
            obj(series, p, ["name", "values"])
            text(series["name"], p + ".name")
            if series["name"] in names:
                fail(p + ".name", "重复序列名")
            names.add(series["name"])
            array(series["values"], p + ".values", len(block["categories"]), len(block["categories"]))
            for j, value in enumerate(series["values"]):
                if value is not None and not number(value):
                    fail(f"{p}.values[{j}]", "须为有限数字或 null；bool 不接受")


def report_warnings(report):
    warnings = []
    if report["mode"] in {"research", "draft"}:
        warnings.append("证据边界：自动校验只检查结构与引用，无法证明公开数据真实性、覆盖完整性或同单位语义，也不能自动检测数据造假；正文是否为定性缺口及数据真实性仍需人工核验，缺口不得用虚构数字补齐。")
        primary = sum(s["kind"] == "primary" for s in report["sources"])
        if report["mode"] == "research":
            warnings.append(f"来源覆盖：当前收录 {primary} 个一手来源，未设置机械数量门槛；未覆盖事项仍属证据缺口，不能据此宣称全面核实。")
        else:
            warnings.append(DRAFT_NOTICE + "；draft 不做价格判断、目标价或交易结论，不得将骨架当作已完成研报。")
            if not primary:
                warnings.append("一手资料缺口：未收录一手来源；仅有二手资料或尚无资料时不做价格判断，二手内容需核实原文。")
            else:
                warnings.append(f"来源覆盖：虽收录 {primary} 个一手来源，当前仍为未完成的 draft 骨架，不据此作价格判断。")
            if not report["sources"]:
                warnings.append("来源缺口：未收录任何资料；正文仅保留定性缺口段落，不生成无依据的数字、图表或 KPI。")
    if not report["kpis"]:
        warnings.append("数据缺口：未提供 KPI 卡片，不能解读为指标为零。")
    for section in report["sections"]:
        for block in section["blocks"]:
            if block["type"] == "chart":
                for series in block["series"]:
                    if any(v is None for v in series["values"]):
                        qualifier = "全序列缺数据，不绘制曲线／柱" if all(v is None for v in series["values"]) else "存在缺值，图形断开、不填零"
                        warnings.append(f"数据缺口：{block['title']}／{series['name']}：{qualifier}。")
            elif block["type"] == "table" and any(v is None for row in block["rows"] for v in row):
                warnings.append(f"数据缺口：{block['title']} 含 null 单元格，以“缺数据”显示。")
    return warnings


def esc(value):
    return html.escape(str(value), quote=True)


def display(value):
    return "缺数据" if value is None else str(value)


def source_note(report, refs, period=None, basis=None):
    sources = {s["id"]: s for s in report["sources"]}
    parts = []
    if period:
        parts.append("周期：" + esc(period))
    if basis:
        parts.append("口径：" + esc(basis))
    for ref in refs:
        source = sources[ref]
        parts.append(f'<a href="#source-{ref}">[{ref}] {esc(source["publisher"])} · {esc(source["published_at"])} · {esc(SOURCE_LABELS[source["kind"]])}</a>')
    return '<p class="source-note">' + "； ".join(parts) + "</p>" if parts else ""


def table_html(title, columns, rows):
    head = "".join(f'<th scope="col">{esc(c)}</th>' for c in columns)
    body = []
    for row in rows:
        cells = []
        for cell in row:
            tone = "num"
            if number(cell):
                tone += " up" if cell > 0 else " down" if cell < 0 else ""
            cells.append(f'<td class="{tone if number(cell) else ""}">{esc(display(cell))}</td>')
        body.append("<tr>" + "".join(cells) + "</tr>")
    return f'<div class="table-scroll" tabindex="0" role="region" aria-label="{esc(title)}精确数据表"><table><caption>{esc(title)}</caption><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def chart_svg(block, anchor):
    width, height = 900, 350
    left, right, top, bottom = 95, 870, 30, 272
    present = [v for s in block["series"] for v in s["values"] if v is not None]
    title_id = anchor + "-svg-title"
    out = [f'<svg class="chart-svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="{title_id}"><title id="{title_id}">{esc(block["title"])}；单位：{esc(block["unit"])}；缺值不填零，精确数据见表格</title>']
    if not present:
        out.append('<text x="450" y="160" text-anchor="middle">全序列缺数据，不绘制曲线或柱形</text></svg>')
        return "".join(out)
    # 先归一化，避免极端有限数字在计算跨度时溢出。
    scale = max(max(abs(v) for v in present), 1)
    low = min(0.0, min(v / scale for v in present))
    high = max(0.0, max(v / scale for v in present))
    if low == high:
        low, high = -1.0, 1.0
    span = high - low

    def y(value):
        return bottom - (value / scale - low) / span * (bottom - top)

    count = len(block["categories"])
    step = (right - left) / count

    def x(index):
        return left + step * (index + 0.5)

    for tick in range(5):
        normalized = low + span * tick / 4
        value = normalized * scale
        pos = bottom - tick / 4 * (bottom - top)
        label = f"{value:.4g}" if value else "0"
        out.append(f'<line class="grid-line" x1="{left}" y1="{pos:.2f}" x2="{right}" y2="{pos:.2f}"/><text x="{left - 10}" y="{pos + 4:.2f}" text-anchor="end">{esc(label)}</text>')
    zero = y(0)
    out.append(f'<line class="zero-axis" x1="{left}" y1="{zero:.2f}" x2="{right}" y2="{zero:.2f}"/><text x="{left}" y="18">{esc(block["unit"])}</text>')
    palette = ["#1a4d8f", "#b7791f", "#7255a0", "#277b85", "#963e64", "#525d6b"]
    for si, series in enumerate(block["series"]):
        color = palette[si % len(palette)]
        if all(v is None for v in series["values"]):
            continue
        if block.get("kind", "line") == "line":
            segment = []
            for i, value in enumerate(series["values"] + [None]):
                if value is None:
                    if len(segment) >= 2:
                        out.append(f'<polyline class="data-line" fill="none" stroke="{color}" points="{" ".join(segment)}"/>')
                    segment = []
                else:
                    segment.append(f"{x(i):.2f},{y(value):.2f}")
                    out.append(f'<circle class="data-point" cx="{x(i):.2f}" cy="{y(value):.2f}" r="4" fill="{color}"><title>{esc(series["name"])} · {esc(block["categories"][i])}：{esc(value)} {esc(block["unit"])}</title></circle>')
        else:
            bar_width = min(48, step * 0.75 / len(block["series"]))
            for i, value in enumerate(series["values"]):
                if value is None:
                    continue
                bx = x(i) + (si - len(block["series"]) / 2) * bar_width
                by = min(y(value), zero)
                fill = "#c0392b" if value > 0 else "#1e8449" if value < 0 else "#525d6b"
                out.append(f'<rect class="data-bar" x="{bx:.2f}" y="{by:.2f}" width="{bar_width * 0.9:.2f}" height="{abs(y(value) - zero):.2f}" fill="{fill}" stroke="{color}"><title>{esc(series["name"])} · {esc(block["categories"][i])}：{esc(value)} {esc(block["unit"])}</title></rect>')
                if value == 0:
                    out.append(f'<circle class="zero-point" cx="{bx + bar_width * .45:.2f}" cy="{zero:.2f}" r="2" fill="{color}"><title>零值：0</title></circle>')
    stride = max(1, math.ceil(count / 8))
    for i, category in enumerate(block["categories"]):
        if i % stride == 0 or i == count - 1:
            label = category if len(category) <= 14 else category[:13] + "…"
            out.append(f'<text x="{x(i):.2f}" y="305" text-anchor="middle"><title>{esc(category)}</title>{esc(label)}</text>')
    out.append('</svg><ul class="chart-legend" aria-label="图表序列及缺值说明">')
    for si, series in enumerate(block["series"]):
        missing = " · 全序列缺数据，不绘制" if all(v is None for v in series["values"]) else " · 缺值断开、不填零" if any(v is None for v in series["values"]) else ""
        out.append(f'<li><span class="legend-dot" style="background:{palette[si % len(palette)]}"></span>{esc(series["name"] + missing)}</li>')
    out.append('</ul><p class="small">同图共用单位；柱形红正绿负，零值显示在 0 轴。轴标签为近似刻度，表格保留精确值。</p>')
    return "".join(out)


def render_block(report, block, anchor):
    kind = block["type"]
    note = source_note(report, block.get("sources", []), block.get("period"), block.get("basis"))
    if kind == "paragraph":
        body = '<p class="prewrap">' + esc(block["text"]) + "</p>"
    elif kind == "heading":
        return f'<h3 id="{anchor}">{esc(block["text"])}</h3>' + note
    elif kind == "callout":
        return f'<aside id="{anchor}" class="callout tone-{block["tone"]}" aria-label="重点提示"><p class="prewrap">{esc(block["text"])}</p>{note}</aside>'
    elif kind == "bullets":
        body = "<ul>" + "".join("<li>" + esc(item) + "</li>" for item in block["items"]) + "</ul>"
    elif kind == "table":
        body = table_html(block["title"], block["columns"], block["rows"])
    elif kind == "flow":
        body = f'<h3>{esc(block["title"])}</h3><ol class="flow" aria-label="{esc(block["title"])}">' + "".join(f'<li><span class="step-number">{i + 1}</span>{esc(step)}</li>' for i, step in enumerate(block["steps"])) + "</ol>"
    elif kind == "cards":
        body = '<div class="cards-grid">' + "".join(f'<article class="mini-card tone-{item["tone"]}"><h3>{esc(item["label"])}</h3><p>{esc(item["text"])}</p></article>' for item in block["items"]) + "</div>"
    else:
        rows = [[category] + [series["values"][i] for series in block["series"]] for i, category in enumerate(block["categories"])]
        columns = ["周期／类别"] + [s["name"] + "（" + block["unit"] + "）" for s in block["series"]]
        body = f'<h3>{esc(block["title"])}</h3><div class="chart-tabs" role="tablist" aria-label="{esc(block["title"])}视图切换" hidden><button type="button" id="{anchor}-tab-chart" role="tab" aria-selected="true" aria-controls="{anchor}-chart" data-view="chart">图表</button><button type="button" id="{anchor}-tab-table" role="tab" aria-selected="false" aria-controls="{anchor}-table" tabindex="-1" data-view="table">精确数据表</button></div><div id="{anchor}-chart" class="chart-panel" role="tabpanel" aria-labelledby="{anchor}-tab-chart">{chart_svg(block, anchor)}</div><div id="{anchor}-table" class="data-panel" role="tabpanel" aria-labelledby="{anchor}-tab-table">{table_html(block["title"] + " · 精确数据", columns, rows)}</div>'
    return f'<div id="{anchor}" class="card {"chart-card" if kind == "chart" else ""}">{body}{note}</div>'


def render_html(report):
    warnings = validate_report(report)
    css = (ROOT / "assets/report.css").read_text(encoding="utf-8")
    js = (ROOT / "assets/report.js").read_text(encoding="utf-8")
    parts = [f'<!DOCTYPE html>\n<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{esc(report["title"])}</title><style>\n{css}\n</style></head><body><a class="skip-link" href="#q1">跳到研究正文</a><main class="wrap"><header class="top"><h1>{esc(report["title"])}</h1><p>{esc(report["subtitle"])}</p><p class="meta">{esc(report["company"])} · {esc(report["ticker"])} · {esc(report["market"])} · 报告日期 {esc(report["report_date"])} · 模式 {esc(report["mode"])}</p><p class="meta">数据截至／来源时点与口径：{esc(report["as_of"])}</p></header>']
    if report["mode"] == "demo":
        parts.append(f'<aside class="demo-notice" role="note">{DEMO_NOTICE}。本页所有数字均为模板测试输入，不对应真实上市公司。</aside>')
    elif report["mode"] == "draft":
        parts.append(f'<aside class="callout tone-risk draft-notice" role="note" aria-label="研究完成状态"><strong>{DRAFT_NOTICE}</strong><p>仅用于整理资料缺口，不做价格判断、目标价或交易结论；缺少一手材料时须补齐并核验原文。</p></aside>')
    parts.append('<section aria-label="首屏四项状态判断" class="verdicts">')
    for item in report["verdicts"]:
        parts.append(f'<article class="verdict tone-{item["tone"]}"><h2>{esc(item["label"])}</h2><p class="status">{esc(item["status"])}</p><p>{esc(item["detail"])}</p></article>')
    parts.append('</section><section class="card" aria-label="核心论点及摘要"><h2 class="plain-heading">核心论点</h2><p class="thesis prewrap">' + esc(report["thesis"]) + '</p><ul>' + "".join('<li>' + esc(t) + '</li>' for t in report["summary"]) + '</ul></section>')
    if report["kpis"]:
        parts.append('<section class="kpis" aria-label="关键指标卡片">')
        for kpi in report["kpis"]:
            parts.append(f'<article class="kpi"><h3>{esc(kpi["label"])}</h3><p class="value">{esc(kpi["value"])}</p><p>{esc(kpi["note"])}</p>{source_note(report, kpi["sources"], kpi["period"])}</article>')
        parts.append('</section>')
    if warnings:
        parts.append('<aside class="callout tone-risk" aria-label="证据边界与数据缺口"><h3>证据边界与数据缺口</h3><ul>' + "".join('<li>' + esc(w) + '</li>' for w in warnings) + '</ul></aside>')
    toc_title = "六问目录" if len(report["sections"]) == 6 else "七问目录"
    parts.append(f'<nav class="toc card" aria-label="{toc_title}"><strong>{toc_title}</strong><ol>' + "".join(f'<li><a href="#{s["id"]}">{esc(s["title"])}</a></li>' for s in report["sections"]) + '</ol><a href="#sources">来源清单</a> · <a href="#disclaimer">免责声明</a></nav><noscript><p class="callout">JavaScript 未启用：静态 SVG 和精确数据表均已显示，无需联网或安装运行环境。</p></noscript>')
    for section in report["sections"]:
        parts.append(f'<section id="{section["id"]}" aria-labelledby="{section["id"]}-title"><h2 id="{section["id"]}-title">{esc(section["title"])}</h2>')
        for i, block in enumerate(section["blocks"]):
            parts.append(render_block(report, block, f'{section["id"]}-b{i + 1}'))
        parts.append('</section>')
    empty_sources = '<p class="small">来源缺口：尚未收录资料，待补齐并核验一手材料。</p>' if not report["sources"] else ""
    parts.append('<section id="sources" class="card" aria-labelledby="sources-title"><h2 id="sources-title">来源清单与核验口径</h2>' + empty_sources + '<ol class="sources-list">')
    for source in report["sources"]:
        label = f'[{source["id"]}] {source["title"]}'
        if urlsplit(source["url"]).scheme == "demo":
            link = esc(label) + ' · <code>' + esc(source["url"]) + '</code>（演示标识，不是可访问证据）'
        else:
            link = f'<a href="{esc(source["url"])}" rel="noopener noreferrer">{esc(label)}</a>'
        parts.append(f'<li id="source-{source["id"]}">{link}<p class="small">{esc(source["publisher"])} · {esc(SOURCE_LABELS[source["kind"]])} · 发布 {esc(source["published_at"])} · 访问 {esc(source["accessed_at"])}</p></li>')
    parts.append(f'</ol></section><footer id="disclaimer" class="disclaimer"><h2 class="plain-heading">免责声明</h2><p>{DISCLAIMER}</p></footer></main><script>\n{js}\n</script></body></html>\n')
    return "\n".join(parts)


def md_text(value):
    value = esc(display(value))
    for char in "\\`*_{}[]()#!|":
        value = value.replace(char, "\\" + char)
    return value.replace("\r\n", "\n").replace("\r", "\n").replace("\n", " / ")


def md_note(report, refs, period=None, basis=None):
    parts = []
    if period:
        parts.append("周期：" + md_text(period))
    if basis:
        parts.append("口径：" + md_text(basis))
    sources = {s["id"]: s for s in report["sources"]}
    for ref in refs:
        s = sources[ref]
        parts.append(f'[{ref}] {md_text(s["publisher"])} · {md_text(s["published_at"])} · {md_text(SOURCE_LABELS[s["kind"]])}')
    return "来源／口径：" + "；".join(parts) if parts else ""


def md_table(columns, rows):
    lines = ["| " + " | ".join(md_text(c) for c in columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    lines.extend("| " + " | ".join(md_text(v) for v in row) + " |" for row in rows)
    return "\n".join(lines)


def render_markdown(report):
    warnings = validate_report(report)
    lines = ["# " + md_text(report["title"]), md_text(report["subtitle"]), f'公司：{md_text(report["company"])} · 代码：{md_text(report["ticker"])} · 市场：{md_text(report["market"])}', f'报告日期：{md_text(report["report_date"])} · 模式：{report["mode"]}', "数据截至／来源时点与口径：" + md_text(report["as_of"])]
    if report["mode"] == "demo":
        lines.append("> " + DEMO_NOTICE + "。所有数字为合成测试输入。")
    elif report["mode"] == "draft":
        lines.append("> **" + DRAFT_NOTICE + "**。仅用于整理资料缺口，不做价格判断、目标价或交易结论；缺少一手材料时须补齐并核验原文。")
    lines += ["## 状态判断", md_table(["标签", "状态", "依据"], [[v["label"], v["status"], v["detail"]] for v in report["verdicts"]]), "## 核心论点", md_text(report["thesis"]), "\n".join("- " + md_text(t) for t in report["summary"])]
    if report["kpis"]:
        lines.append("## 关键指标")
        for kpi in report["kpis"]:
            lines += [f'### {md_text(kpi["label"])}：{md_text(kpi["value"])}', md_text(kpi["note"]), md_note(report, kpi["sources"], kpi["period"])]
    if warnings:
        lines += ["## 证据边界与数据缺口", "\n".join("- " + md_text(w) for w in warnings)]
    toc_title = "六问目录" if len(report["sections"]) == 6 else "七问目录"
    lines.append("## " + toc_title + "\n" + "\n".join(f'- [{md_text(s["title"])}](#{s["id"]})' for s in report["sections"]))
    for section in report["sections"]:
        lines += [f'<a id="{section["id"]}"></a>', "## " + md_text(section["title"])]
        for block in section["blocks"]:
            kind = block["type"]
            if kind in {"paragraph", "heading", "callout"}:
                prefix = "### " if kind == "heading" else "> " if kind == "callout" else ""
                lines.append(prefix + md_text(block["text"]))
            elif kind == "bullets":
                lines.append("\n".join("- " + md_text(t) for t in block["items"]))
            elif kind == "flow":
                lines += ["### " + md_text(block["title"]), "\n".join(f'{i + 1}. {md_text(t)}' for i, t in enumerate(block["steps"]))]
            elif kind == "cards":
                lines.append("\n".join(f'- **{md_text(c["label"])}**：{md_text(c["text"])}' for c in block["items"]))
            elif kind == "table":
                lines += ["### " + md_text(block["title"]), md_table(block["columns"], block["rows"])]
            else:
                columns = ["周期／类别"] + [s["name"] + "（" + block["unit"] + "）" for s in block["series"]]
                rows = [[c] + [s["values"][i] for s in block["series"]] for i, c in enumerate(block["categories"])]
                lines += ["### " + md_text(block["title"]) + "（精确数据）", md_table(columns, rows), "图表说明：null 为缺数据，不填零；所有序列共用单位。"]
            note = md_note(report, block.get("sources", []), block.get("period"), block.get("basis"))
            if note:
                lines.append(note)
    lines.append("## 来源清单")
    if not report["sources"]:
        lines.append("来源缺口：尚未收录资料，待补齐并核验一手材料。")
    for source in report["sources"]:
        lines.append(f'- [{source["id"]}] {md_text(source["title"])} — {md_text(source["publisher"])}；{md_text(SOURCE_LABELS[source["kind"]])}；发布 {md_text(source["published_at"])}；访问 {md_text(source["accessed_at"])}；URL：{esc(source["url"])}')
    lines += ["## 免责声明", DISCLAIMER]
    return "\n\n".join(lines) + "\n"
