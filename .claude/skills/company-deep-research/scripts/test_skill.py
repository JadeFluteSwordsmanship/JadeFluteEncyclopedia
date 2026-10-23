#!/usr/bin/env python3
"""标准库 unittest 入口；直接执行或 python -I 执行均可，不生成 pycache。"""
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

import copy
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
import unittest
from unittest import mock
import zipfile

from report_core import (DEMO_NOTICE, DRAFT_NOTICE, DISCLAIMER, ROOT, ReportError, chart_svg,
                         load_report, render_html, render_markdown, validate_report)
from validate_report import OfflineHTMLParser, validate_html


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.scripts = []
        self.script = None
        self.styles = []
        self.style = None
        self.id_counts = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        identity = attrs.get("id")
        if identity:
            self.id_counts[identity] = self.id_counts.get(identity, 0) + 1
        if tag == "script":
            self.script = []
        if tag == "style":
            self.style = []

    def handle_data(self, data):
        if self.script is not None:
            self.script.append(data)
        if self.style is not None:
            self.style.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.script is not None:
            self.scripts.append("".join(self.script))
            self.script = None
        if tag == "style" and self.style is not None:
            self.styles.append("".join(self.style))
            self.style = None

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)


def chart(report, index=0):
    # 校验用的默认样本应为同单位多序列，不依赖章节移动后的排列位置。
    charts = [b for s in report["sections"] for b in s["blocks"] if b["type"] == "chart" and len(b["series"]) > 1]
    return charts[index]


def numeric_table(report):
    return next(b for s in report["sections"] for b in s["blocks"] if b.get("title") == "模拟损益与现金对照 — 所有数字均为合成")


def research_fixture():
    return {
        "schema_version": 1, "title": "公开材料结构测试", "company": "测试主体",
        "ticker": "TEST", "market": "美股", "report_date": "2026-10-23",
        "subtitle": "仅测试结构，不构成事实判断", "as_of": "来源时点 2026-10-23；本例没有财务观测值",
        "mode": "research", "thesis": "资料覆盖存在缺口，不作投资结论。", "summary": ["需补齐公开材料。"],
        "verdicts": [{"label": label, "status": "待核验", "detail": "资料不足", "tone": "neutral"} for label in ["盈利兑现", "逆境反转", "估值压缩", "预期提高"]],
        "kpis": [],
        "sections": [{"id": f"q{i}", "title": f"问题 {i}", "blocks": [{"type": "paragraph", "text": "证据缺口：尚未核验完整公开材料。", "sources": ["S1"]}]} for i in range(1, 7)],
        "sources": [{"id": "S1", "title": "URL 语法测试夹具，不是真实证据", "url": "https://example.invalid/source", "publisher": "测试发布方", "published_at": "2026-10-23", "accessed_at": "2026-10-23", "kind": "primary"}],
    }


def draft_fixture(with_secondary=False):
    report = research_fixture()
    report["mode"] = "draft"
    report["title"] = "六问资料缺口骨架"
    report["subtitle"] = "仅整理待核验材料，不做价格判断"
    report["as_of"] = "材料整理时点 2026-10-23；未核验一手资料，不含财务观测值"
    topics = ["行业", "商业模式", "竞争与分层颠覆", "估值非共识", "财务风险", "四状态综合"]
    for section, topic in zip(report["sections"], topics):
        section["title"] = topic + "：资料缺口待核验"
        section["blocks"] = [{"type": "paragraph", "text": "资料缺口：尚无可核验的一手材料，仅列待补资料，不作价格判断。"}]
        if with_secondary:
            section["blocks"][0]["sources"] = ["S1"]
    if with_secondary:
        report["sources"][0]["kind"] = "secondary"
    else:
        report["sources"] = []
    return report


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.example = load_report(ROOT / "examples/demo-report.json")
        cls.html = render_html(cls.example)
        cls.markdown = render_markdown(cls.example)

    def setUp(self):
        self.report = copy.deepcopy(self.example)

    def rejected(self, report=None):
        with self.assertRaises(ReportError):
            validate_report(self.report if report is None else report)

    def run_cli(self, root, script, *args, cwd=None, env=None):
        result = subprocess.run([sys.executable, "-I", str(root / "scripts" / script), *map(str, args)], cwd=cwd, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_demo_valid_and_components_complete(self):
        warnings = validate_report(self.report)
        self.assertTrue(warnings)
        self.assertEqual(len(self.report["kpis"]), 6)
        self.assertEqual({b["type"] for s in self.report["sections"] for b in s["blocks"]}, {"paragraph", "heading", "callout", "bullets", "table", "chart", "flow", "cards"})
        validate_html(self.report, self.html)

    def test_example_outputs_match_current_templates(self):
        html_path = ROOT / "examples/demo-report.html"
        markdown_path = ROOT / "examples/demo-report.md"
        self.assertEqual(html_path.read_text(encoding="utf-8"), self.html)
        self.assertEqual(markdown_path.read_text(encoding="utf-8"), self.markdown)
        validate_html(self.report, html_path.read_text(encoding="utf-8"))

    def test_demo_notice_is_automatic_and_prominent(self):
        self.report["subtitle"] = "界面示例"
        page = render_html(self.report)
        self.assertIn(f'class="demo-notice" role="note">{DEMO_NOTICE}', page)
        self.assertIn(DEMO_NOTICE, render_markdown(self.report))
        self.assertIn("DEMO Research Systems", page)

    def test_schema_version_strict(self):
        for value in [2, True, "1", 1.0, None]:
            with self.subTest(value=value):
                self.report["schema_version"] = value
                self.rejected()

    def test_required_root_fields_missing_or_empty(self):
        for key in ["title", "company", "ticker", "subtitle", "as_of", "thesis", "mode", "report_date"]:
            for value in [None, "", "  "]:
                with self.subTest(key=key, value=value):
                    report = copy.deepcopy(self.example)
                    report[key] = value
                    self.rejected(report)
            report = copy.deepcopy(self.example)
            del report[key]
            self.rejected(report)

    def test_no_unknown_fields_or_raw_html_blocks(self):
        for path in ["root", "block", "series"]:
            with self.subTest(path=path):
                report = copy.deepcopy(self.example)
                if path == "root":
                    report["raw_html"] = "<b>禁止</b>"
                elif path == "block":
                    report["sections"][0]["blocks"][0]["html"] = "<b>禁止</b>"
                else:
                    chart(report)["series"][0]["unit"] = "%"
                self.rejected(report)
        self.report["sections"][0]["blocks"][0] = {"type": "html", "text": "<b>禁止</b>"}
        self.rejected()

    def test_six_sections_and_stable_order(self):
        variants = [self.example["sections"][:5], self.example["sections"] + [self.example["sections"][0]], list(reversed(self.example["sections"]))]
        for sections in variants:
            with self.subTest(count=len(sections)):
                self.report["sections"] = copy.deepcopy(sections)
                self.rejected()
        self.report = copy.deepcopy(self.example)
        self.report["sections"][1]["id"] = "q1"
        self.rejected()

    def test_four_verdicts_labels_and_tones(self):
        for length in [0, 3, 5]:
            report = copy.deepcopy(self.example)
            report["verdicts"] = (report["verdicts"] * 2)[:length]
            self.rejected(report)
        for key, value in [("label", "别的标签"), ("tone", "green"), ("status", ""), ("detail", None)]:
            report = copy.deepcopy(self.example)
            report["verdicts"][0][key] = value
            self.rejected(report)

    def test_kpi_bounds_and_missing_values(self):
        self.report["kpis"] = []
        self.assertTrue(any("KPI" in w for w in validate_report(self.report)))
        self.report["kpis"] = self.example["kpis"] + [self.example["kpis"][0]]
        self.rejected()
        for value in [None, "", True, float("nan"), float("inf")]:
            report = copy.deepcopy(self.example)
            report["kpis"][0]["value"] = value
            self.rejected(report)
        for key in ["value", "sources", "period"]:
            report = copy.deepcopy(self.example)
            del report["kpis"][0][key]
            self.rejected(report)

    def test_market_and_ticker_formats(self):
        for market, ticker in [("A股", "600001"), ("港股", "00700"), ("美股", "BRK.B"), ("美股", "TEST-A")]:
            with self.subTest(market=market, ticker=ticker):
                self.report["market"], self.report["ticker"] = market, ticker
                validate_report(self.report)
        for market, ticker in [("A股", "60001"), ("港股", "0700"), ("美股", "demo"), ("美股", "T EST"), ("美股", "TEST<script>"), ("其他", "DEMO")]:
            with self.subTest(market=market, ticker=ticker):
                self.report["market"], self.report["ticker"] = market, ticker
                self.rejected()

    def test_dates_and_source_timestamps(self):
        for value in ["2026-02-30", "2026-2-3", "2026-10-23T09:00:00Z", "today"]:
            report = copy.deepcopy(self.example)
            report["report_date"] = value
            self.rejected(report)
        for value in ["2026-10-23", "2026-10-23T10:00:00Z", "2026-10-23T10:00:00+08:00"]:
            self.report["sources"][0]["published_at"] = value
            validate_report(self.report)
        for value in ["2026-13-23", "2026-10-23T10:00:00", "2026-10-23T30:00:00Z", "2026-10-23T10:00:00+12:60", "2026-10-23T10:00:00+24:00", ""]:
            self.report["sources"][0]["published_at"] = value
            self.rejected()

    def test_duplicate_and_invalid_source_ids(self):
        for value in ["S1", "s2", "S0", "S01", "S-2", "S2\" onclick=\"evil"]:
            with self.subTest(value=value):
                self.report["sources"][1]["id"] = value
                self.rejected()

    def test_missing_duplicate_and_non_string_references(self):
        for refs in [["S99"], ["S1", "S1"], [1], "S1", ["S0"]]:
            with self.subTest(refs=refs):
                self.report["sections"][0]["blocks"][0]["sources"] = refs
                self.rejected()

    def test_required_sources_and_period_numeric_blocks(self):
        for target in ["chart", "table", "kpi"]:
            for key in ["sources", "period"]:
                for operation in ["missing", "empty"]:
                    with self.subTest(target=target, key=key, operation=operation):
                        report = copy.deepcopy(self.example)
                        block = chart(report) if target == "chart" else numeric_table(report) if target == "table" else report["kpis"][0]
                        if operation == "missing":
                            del block[key]
                        else:
                            block[key] = [] if key == "sources" else ""
                        self.rejected(report)

    def test_numeric_strings_cannot_bypass_table_provenance(self):
        block = numeric_table(self.report)
        block["rows"] = [["模拟收入", "123.5", "-5", "0"]]
        del block["sources"]
        self.rejected()

    def test_rectangular_table_and_scalar_cells(self):
        for rows in [[["短行"]], [["长", 1, 2, 3, 4]], [["bool", True, 1, 2]], [["嵌套", {}, 1, 2]], [["空文本", "", 1, 2]], [["非有限", float("inf"), 1, 2]], []]:
            with self.subTest(rows=rows):
                numeric_table(self.report)["rows"] = rows
                self.rejected()

    def test_chart_alignment_finite_and_bool(self):
        for values in [[1], [1, 2, 3, 4], [True, 2, 3], [1, float("inf"), 3], [1, float("nan"), 3], [1, "2", 3], [1, 10 ** 400, 3]]:
            with self.subTest(values=values):
                chart(self.report)["series"][0]["values"] = values
                self.rejected()

    def test_chart_names_kind_and_units(self):
        for key, value in [("kind", "pie"), ("categories", []), ("unit", "")]:
            report = copy.deepcopy(self.example)
            chart(report)[key] = value
            self.rejected(report)
        chart(self.report)["series"][1]["name"] = chart(self.report)["series"][0]["name"]
        self.rejected()
        self.report = copy.deepcopy(self.example)
        chart(self.report)["series"][0]["unit"] = "%"
        self.rejected()

    def test_null_line_gaps_are_not_connected(self):
        block = copy.deepcopy(chart(self.report))
        block["categories"] = ["甲", "乙", "丙", "丁", "戊"]
        block["series"] = [{"name": "含缺值", "values": [-2, 0, None, 1, 2]}]
        svg = chart_svg(block, "q1-b1")
        self.assertEqual(svg.count('class="data-line"'), 2)
        self.assertEqual(svg.count('class="data-point"'), 4)
        self.assertIn("缺值断开、不填零", svg)
        self.assertIn('class="zero-axis"', svg)

    def test_all_null_and_partial_null_series(self):
        block = copy.deepcopy(chart(self.report))
        block["series"] = [{"name": "全空", "values": [None, None, None]}]
        svg = chart_svg(block, "q1-b1")
        self.assertIn("全序列缺数据", svg)
        for mark in ["data-line", "data-point", "data-bar"]:
            self.assertNotIn(mark, svg)
        block["series"].append({"name": "有数据", "values": [-1, 0, 1]})
        svg = chart_svg(block, "q1-b1")
        self.assertIn("全空 · 全序列缺数据，不绘制", svg)
        self.assertEqual(svg.count('class="data-point"'), 3)

    def test_negative_bar_zero_and_null(self):
        block = copy.deepcopy(chart(self.report))
        block["kind"] = "bar"
        block["categories"] = ["负", "空", "零", "正"]
        block["series"] = [{"name": "示例", "values": [-2.5, None, 0, 3.125]}]
        svg = chart_svg(block, "q1-b1")
        self.assertEqual(svg.count('class="data-bar"'), 3)
        self.assertIn('fill="#1e8449"', svg)
        self.assertIn('fill="#c0392b"', svg)
        self.assertIn('class="zero-point"', svg)
        self.assertIn('class="zero-axis"', svg)
        for height in re.findall(r'<rect[^>]+height="([^"]+)"', svg):
            self.assertGreaterEqual(float(height), 0)

    def test_all_zero_and_extreme_finite_chart_coordinates(self):
        block = copy.deepcopy(chart(self.report))
        for values in [[0, 0, 0], [-1e308, 0, 1e308], [1e-300, 0, -1e-300]]:
            block["series"] = [{"name": "边界", "values": values}]
            svg = chart_svg(block, "q1-b1")
            self.assertNotRegex(svg, r'="(?:nan|inf|-inf)"')
            for coord in re.findall(r'(?:cx|cy|x1|y1|x2|y2)="([0-9.-]+)"', svg):
                self.assertLessEqual(abs(float(coord)), 1000)

    def test_malicious_html_is_text_in_every_component(self):
        payload = "\"><script>alert(\"中文\")</script><img src=x onerror=alert(1)>&'\""
        self.report["title"] = payload
        self.report["subtitle"] = payload
        self.report["thesis"] = payload
        self.report["summary"] = [payload]
        self.report["company"] = payload
        self.report["kpis"][0]["value"] = payload
        self.report["verdicts"][0]["detail"] = payload
        self.report["sources"][0]["title"] = payload
        self.report["sources"][0]["publisher"] = payload
        for section in self.report["sections"]:
            section["title"] = payload
            for block in section["blocks"]:
                for key in ["title", "text", "basis", "unit", "period"]:
                    if key in block:
                        block[key] = payload
                if block["type"] == "table":
                    block["columns"][0] = payload
                    block["rows"][0][0] = payload
                    block["period"] = payload
                if block["type"] == "chart":
                    block["categories"][0] = payload
                    block["series"][0]["name"] = payload
                if block["type"] == "flow":
                    block["steps"][0] = payload
                if block["type"] == "bullets":
                    block["items"][0] = payload
                if block["type"] == "cards":
                    block["items"][0]["label"] = payload
                    block["items"][0]["text"] = payload
        page = render_html(self.report)
        self.assertIn("&lt;script&gt;", page)
        self.assertIn("&quot;中文&quot;", page)
        self.assertIn("&#x27;", page)
        parser = PageParser()
        parser.feed(page)
        self.assertEqual(len(parser.scripts), 1)
        self.assertFalse(any(tag == "img" for tag, _ in parser.tags))
        self.assertFalse(any(k.startswith("on") for _, attrs in parser.tags for k in attrs))
        self.assertNotIn(payload, parser.scripts[0])
        md = render_markdown(self.report)
        self.assertNotIn("<script>", md)
        self.assertIn("&lt;script&gt;", md)
        validate_html(self.report, page)

    def test_javascript_and_unsafe_urls_rejected(self):
        bad = ["javascript:alert(1)", "JaVaScRiPt:alert(1)", "data:text/html,test", "file:///tmp/test", "//example.invalid/x", "https://example.invalid/\"onclick=\"evil", "https://example.invalid/<script>", "https://example.invalid/\n", "https://example.invalid/\\evil", "https://user:pass@example.invalid/", "https:///missing", "https://example.invalid:bad", "https://example.invalid/%0aevil", "demo://", "https://example.invalid/%5cevil"]
        for url in bad:
            with self.subTest(url=url):
                self.report["sources"][0]["url"] = url
                self.rejected()

    def test_safe_url_query_is_attribute_escaped(self):
        self.report["sources"][0]["url"] = "https://example.invalid/source?a=1&b=2"
        page = render_html(self.report)
        self.assertIn('href="https://example.invalid/source?a=1&amp;b=2"', page)
        parser = PageParser()
        parser.feed(page)
        self.assertTrue(any(attrs.get("href") == "https://example.invalid/source?a=1&b=2" for _, attrs in parser.tags))

    def test_research_minimum_one_primary_not_eight(self):
        report = research_fixture()
        warnings = validate_report(report)
        self.assertTrue(any("1 个一手来源" in w for w in warnings))
        page = render_html(report)
        self.assertIn("证据缺口", page)
        self.assertIn("无法证明公开数据真实性", page)
        self.assertNotIn('class="demo-notice"', page)
        self.assertIn("证据缺口", render_markdown(report))

    def test_research_without_primary_rejected(self):
        report = research_fixture()
        report["sources"][0]["kind"] = "secondary"
        self.rejected(report)
        report["sources"] = []
        self.rejected(report)

    def test_research_demo_url_and_source_kind_rejected(self):
        for mutation in ["kind", "url"]:
            with self.subTest(mutation=mutation):
                report = research_fixture()
                if mutation == "kind":
                    report["sources"].append({**report["sources"][0], "id": "S2", "kind": "demo"})
                else:
                    report["sources"][0]["url"] = "demo://test/source"
                self.rejected(report)

    def test_primary_research_synthetic_business_and_negative_statements_valid(self):
        terms = ["业务包含 synthetic data 产品", "业务包含合成数据产品", "不使用合成数据填补资料缺口", "本主体不是虚构公司", "not a fictional company", "not synthetic data"]
        for term in terms:
            with self.subTest(term=term):
                report = research_fixture()
                report["title"] = term
                report["company"] = term
                report["subtitle"] = term
                report["thesis"] = term
                report["summary"] = [term]
                report["sections"][0]["blocks"][0]["text"] = term
                report["sources"][0]["title"] = term
                warnings = validate_report(report)
                page = render_html(report)
                markdown = render_markdown(report)
                self.assertIn(term, page)
                self.assertIn(term, markdown)
                self.assertTrue(any("不能自动检测数据造假" in w for w in warnings))
                validate_html(report, page)

    def test_draft_zero_sources_rendering_no_invented_components(self):
        report = draft_fixture()
        warnings = validate_report(report)
        page, markdown = render_html(report), render_markdown(report)
        self.assertIn('<strong>' + DRAFT_NOTICE + '</strong>', page)
        self.assertIn('> **' + DRAFT_NOTICE + '**', markdown)
        self.assertLess(page.index('class="callout tone-risk draft-notice"'), page.index('class="verdicts"'))
        self.assertLess(markdown.index('> **' + DRAFT_NOTICE), markdown.index('## 状态判断'))
        self.assertNotIn(DEMO_NOTICE, page)
        self.assertNotIn('<svg', page)
        self.assertNotIn('class="chart-card"', page)
        self.assertNotIn('class="kpis"', page)
        self.assertNotIn('class="data-panel"', page)
        self.assertNotIn('class="source-note"', page)
        self.assertIn("尚未收录资料", page)
        self.assertIn("尚未收录资料", markdown)
        self.assertTrue(any("未收录一手来源" in w and "不做价格判断" in w for w in warnings))
        self.assertTrue(any("未收录任何资料" in w for w in warnings))
        self.assertTrue(any("不能自动检测数据造假" in w for w in warnings))
        self.assertTrue(markdown.endswith(DISCLAIMER + "\n"))
        for i in range(1, 7):
            self.assertIn(f'id="q{i}"', page)
            self.assertIn(f'href="#q{i}"', page)
        validate_html(report, page)

    def test_draft_secondary_sources_allowed_but_not_complete_research(self):
        report = draft_fixture(with_secondary=True)
        warnings = validate_report(report)
        for output in [render_html(report), render_markdown(report)]:
            self.assertIn(DRAFT_NOTICE, output)
            self.assertIn("二手来源／需核实原文", output)
            self.assertIn("不做价格判断", output)
            self.assertIn("[S1]", output)
        self.assertTrue(any("未收录一手来源" in w for w in warnings))
        report["mode"] = "research"
        self.rejected(report)

    def test_draft_with_primary_still_shows_unfinished_notice(self):
        report = draft_fixture(with_secondary=True)
        report["sources"][0]["kind"] = "primary"
        warnings = validate_report(report)
        self.assertTrue(any("1 个一手来源" in w and "未完成" in w for w in warnings))
        self.assertFalse(any("未收录一手来源" in w for w in warnings))
        self.assertIn(DRAFT_NOTICE, render_html(report))
        self.assertIn(DRAFT_NOTICE, render_markdown(report))

    def test_draft_demo_kind_and_url_rejected(self):
        for kind in ["primary", "secondary", "assumption", "demo"]:
            for url in ["demo://test/source", "DEMO://test/source", "https://example.invalid/source"]:
                with self.subTest(kind=kind, url=url):
                    report = draft_fixture(with_secondary=True)
                    report["sources"][0]["kind"] = kind
                    report["sources"][0]["url"] = url
                    if kind == "demo" or url.lower().startswith("demo://"):
                        self.rejected(report)
                    else:
                        validate_report(report)
        self.report["mode"] = "draft"
        self.rejected()
        self.report["mode"] = "research"
        self.rejected()
        self.report["mode"] = "demo"
        validate_report(self.report)

    def test_draft_no_sources_only_qualitative_gap_paragraphs(self):
        variants = [
            {"type": "heading", "text": "资料缺口"},
            {"type": "callout", "text": "资料缺口", "tone": "risk"},
            {"type": "bullets", "items": ["资料缺口"]},
            {"type": "table", "title": "资料缺口", "columns": ["事项"], "rows": [["待核验"]]},
            {"type": "flow", "title": "资料缺口", "steps": ["待核验"]},
            {"type": "cards", "items": [{"label": "资料缺口", "text": "待核验", "tone": "neutral"}]},
        ]
        for block in variants:
            with self.subTest(kind=block["type"]):
                report = draft_fixture()
                report["sections"][0]["blocks"] = [block]
                self.rejected(report)
        report = draft_fixture()
        report["sections"][0]["blocks"][0]["sources"] = ["S1"]
        self.rejected(report)
        report = draft_fixture()
        report["sections"][0]["blocks"][0]["text"] = "合成数据产品资料未核验；不是虚构公司声明，也不能替代一手来源。"
        validate_report(report)

    def test_draft_numeric_components_cannot_bypass_references_or_period(self):
        prototypes = {
            "chart": {"type": "chart", "title": "数值校验夹具，非事实资料", "categories": ["观察甲", "观察乙"], "series": [{"name": "观测", "values": [-1.25, None]}], "unit": "金额单位", "period": "测试窗口", "sources": ["S1"]},
            "table": {"type": "table", "title": "数值校验夹具，非事实资料", "columns": ["观测"], "rows": [[0], [None]], "period": "测试窗口", "sources": ["S1"]},
            "kpi": {"label": "数值校验夹具，非事实资料", "value": 0, "note": "仅用于结构测试", "period": "测试窗口", "sources": ["S1"]},
        }
        for kind, prototype in prototypes.items():
            for has_sources in [False, True]:
                for key in ["sources", "period"]:
                    for operation in ["missing", "empty", "invalid"]:
                        with self.subTest(kind=kind, has_sources=has_sources, key=key, operation=operation):
                            report = draft_fixture(with_secondary=has_sources)
                            block = copy.deepcopy(prototype)
                            if operation == "missing":
                                del block[key]
                            elif operation == "empty":
                                block[key] = [] if key == "sources" else ""
                            else:
                                block[key] = ["S99"] if key == "sources" else None
                            if kind == "kpi":
                                report["kpis"] = [block]
                            else:
                                report["sections"][0]["blocks"].append(block)
                            self.rejected(report)
        report = draft_fixture()
        block = copy.deepcopy(prototypes["chart"])
        block["series"][0]["values"] = [None, None]
        block["sources"] = []
        report["sections"][0]["blocks"].append(block)
        self.rejected(report)
        for kind, prototype in prototypes.items():
            report = draft_fixture(with_secondary=True)
            if kind == "kpi":
                report["kpis"] = [copy.deepcopy(prototype)]
            else:
                report["sections"][0]["blocks"].append(copy.deepcopy(prototype))
            validate_report(report)
            self.assertIn(DRAFT_NOTICE, render_html(report))

    def test_draft_cli_zero_sources_and_secondary(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            for with_secondary in [False, True]:
                report = draft_fixture(with_secondary)
                source, output, markdown = work / "draft.json", work / "draft.html", work / "draft.md"
                source.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
                result = self.run_cli(ROOT, "render_report.py", source, output, "--markdown", markdown, cwd=work)
                self.assertIn("未收录一手来源", result.stderr)
                self.assertIn("不做价格判断", result.stderr)
                self.run_cli(ROOT, "validate_report.py", source, "--html", output, cwd=work)
                self.assertEqual(output.read_text(encoding="utf-8"), render_html(report))
                self.assertEqual(markdown.read_text(encoding="utf-8"), render_markdown(report))

    def test_mode_values_and_source_minimum_remain_strict(self):
        for mode in ["", "DRAFT", "unknown", None]:
            report = draft_fixture()
            report["mode"] = mode
            self.rejected(report)
        for mode in ["research", "demo"]:
            report = draft_fixture()
            report["mode"] = mode
            self.rejected(report)

    def test_all_optional_sources_and_table_basis(self):
        section = next(s for s in self.report["sections"] if s["id"] == "q2")
        for block in section["blocks"]:
            block.pop("sources", None)
        validate_report(self.report)
        self.assertIn("口径：定性示范", render_html(self.report))
        self.assertIn("口径：定性示范", render_markdown(self.report))

    def test_no_empty_sections_or_component_items(self):
        mutations = [("section", None), ("flow", "steps"), ("cards", "items"), ("bullets", "items"), ("table", "columns")]
        for kind, key in mutations:
            report = copy.deepcopy(self.example)
            if kind == "section":
                report["sections"][0]["blocks"] = []
            else:
                block = next(b for s in report["sections"] for b in s["blocks"] if b["type"] == kind)
                block[key] = []
            self.rejected(report)

    def test_json_duplicate_keys_and_nonstandard_numbers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            for content in ['{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}', '{"a":-Infinity}', '{bad']:
                path.write_text(content, encoding="utf-8")
                with self.subTest(content=content), self.assertRaises(ReportError):
                    load_report(path)

    def test_html_assets_fully_inline_and_platform_free(self):
        parser = PageParser()
        parser.feed(self.html)
        self.assertEqual(len(parser.scripts), 1)
        self.assertEqual(len(parser.styles), 1)
        for tag, attrs in parser.tags:
            self.assertNotIn(tag, {"link", "iframe", "img", "object", "embed", "base"})
            self.assertNotIn("src", attrs)
        for token in ["cdn.", "echarts", "inject.js", "data-page-node-id", "data-pnid", "fetch(", "XMLHttpRequest", "@import", "url(", "node_modules"]:
            self.assertNotIn(token, self.html)
        offline = OfflineHTMLParser()
        offline.feed(self.html)
        self.assertFalse(offline.errors)

    def test_offline_render_without_network(self):
        with mock.patch.object(socket.socket, "connect", side_effect=AssertionError("离线测试不允许网络")), mock.patch.object(socket, "create_connection", side_effect=AssertionError("离线测试不允许网络")):
            self.assertEqual(render_html(self.report), self.html)
            self.assertEqual(render_markdown(self.report), self.markdown)

    def test_mobile_print_and_style_contract(self):
        css = (ROOT / "assets/report.css").read_text(encoding="utf-8")
        for token in ["max-width:1180px", "#f6f7f9", "#1a4d8f", "#c0392b", "#1e8449", "border-bottom:3px solid var(--blue)", "border-left:5px solid var(--blue)", "@media(max-width:900px)", "@media(max-width:600px)", "@media print", "grid-template-columns:1fr", "overflow-x:auto", ".data-panel{display:block!important}"]:
            self.assertIn(token, css)
        self.assertIn('name="viewport"', self.html)

    def test_ascii_anchors_unique_and_reachable(self):
        parser = PageParser()
        parser.feed(self.html)
        self.assertTrue(all(v == 1 for v in parser.id_counts.values()))
        self.assertTrue(all(re.fullmatch(r"[A-Za-z0-9-]+", identity) for identity in parser.id_counts))
        for i in range(1, 7):
            self.assertIn(f"q{i}", parser.id_counts)
            self.assertIn(f'href="#q{i}"', self.html)
        for tag, attrs in parser.tags:
            for key in ["href", "aria-controls", "aria-labelledby"]:
                value = attrs.get(key, "")
                if key == "href" and not value.startswith("#"):
                    continue
                if value:
                    self.assertIn(value.lstrip("#"), parser.id_counts)

    def test_svg_tables_tabs_accessibility_and_no_js_fallback(self):
        parser = PageParser()
        parser.feed(self.html)
        svgs = [attrs for tag, attrs in parser.tags if tag == "svg"]
        self.assertGreaterEqual(len(svgs), 6)
        self.assertTrue(all(attrs.get("role") == "img" and attrs.get("aria-labelledby") for attrs in svgs))
        self.assertTrue(all(attrs.get("scope") == "col" for tag, attrs in parser.tags if tag == "th"))
        tablists = [attrs for _, attrs in parser.tags if attrs.get("role") == "tablist"]
        self.assertTrue(tablists)
        self.assertTrue(all("hidden" in attrs for attrs in tablists))
        panels = [attrs for _, attrs in parser.tags if attrs.get("role") == "tabpanel"]
        self.assertTrue(all("hidden" not in attrs for attrs in panels))
        self.assertIn("<noscript>", self.html)
        self.assertIn("ArrowLeft", parser.scripts[0])
        self.assertIn("aria-selected", parser.scripts[0])
        self.assertNotIn("innerHTML", parser.scripts[0])

    def test_exact_data_in_table_and_markdown(self):
        for token in ["-26.125", "91.25", "101.75", "-12.125", "4.875", "缺数据"]:
            self.assertIn(token, self.html)
            self.assertIn(token, self.markdown)
        self.assertNotIn("None", self.html)
        self.assertIn('>0</td>', self.html)

    def test_sources_near_cards_and_charts(self):
        self.assertEqual(self.html.count('class="source-note"'), sum(bool(b.get("sources") or b.get("period") or b.get("basis")) for s in self.report["sections"] for b in s["blocks"]) + len(self.report["kpis"]))
        self.assertIn('href="#source-S1"', self.html)
        self.assertIn("2026-10-23T09:00:00+08:00", self.html)
        report = research_fixture()
        report["sources"].append({**report["sources"][0], "id": "S2", "kind": "secondary"})
        report["sections"][0]["blocks"][0]["sources"] = ["S1", "S2"]
        self.assertIn("二手来源／需核实原文", render_html(report))
        self.assertIn("二手来源／需核实原文", render_markdown(report))

    def test_markdown_metadata_six_sections_citations_disclaimer(self):
        for key in ["DEMO Research Systems", "DEMO", "美股", "报告日期", "来源时点", "[S1]", "## 来源清单", "## 免责声明", DEMO_NOTICE, DISCLAIMER]:
            self.assertIn(key, self.markdown)
        for i in range(1, 7):
            self.assertIn(f'<a id="q{i}"></a>', self.markdown)
        self.assertTrue(self.markdown.endswith(DISCLAIMER + "\n"))
        self.assertEqual(self.html.count(DISCLAIMER), 1)

    def test_markdown_special_characters_cannot_break_table_or_inject_html(self):
        numeric_table(self.report)["rows"][0][0] = '中文 | "引用"\n<script>坏文本</script> [链接](javascript:alert(1))'
        md = render_markdown(self.report)
        self.assertIn("\\|", md)
        self.assertIn("&lt;script&gt;", md)
        self.assertIn("\\[链接\\]\\(", md)
        self.assertNotIn("<script>", md)

    def test_html_validation_rejects_tampering_and_external_assets(self):
        for content in [self.html.replace("DEMO Research Systems", "改写公司", 1), self.html.replace("<head>", '<head><script src="https://example.invalid/test.js"></script>', 1), self.html.replace('id="q2"', 'id="q1"', 1), self.html.replace('scope="col"', 'scope="row"', 1), self.html.replace('href="#q2"', 'href="#missing"', 1)]:
            with self.assertRaises(ReportError):
                validate_html(self.report, content)

    def test_cli_render_and_validate_and_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            output, markdown = work / "报告.html", work / "报告.md"
            self.run_cli(ROOT, "render_report.py", ROOT / "examples/demo-report.json", output, "--markdown", markdown, cwd=work)
            self.run_cli(ROOT, "validate_report.py", ROOT / "examples/demo-report.json", "--html", output, cwd=work)
            self.assertEqual(output.read_text(encoding="utf-8"), self.html)
            self.assertEqual(markdown.read_text(encoding="utf-8"), self.markdown)
            source = work / "input.json"
            source.write_text(json.dumps(self.report, ensure_ascii=False), encoding="utf-8")
            cases = [["render_report.py", source, source], ["render_report.py", source, output, "--markdown", output], ["render_report.py", source, work / "missing" / "report.html"], ["validate_report.py", work / "not-there.json"]]
            for args in cases:
                result = subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / args[0]), *map(str, args[1:])], cwd=work, capture_output=True, text=True, timeout=30)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(load_report(source), self.report)
            del self.report["sections"][0]
            source.write_text(json.dumps(self.report, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, "-I", str(ROOT / "scripts/render_report.py"), str(source), str(output)], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(output.read_text(encoding="utf-8"), self.html)

    def test_migration_isolated_python_no_home_or_cwd_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            root = work / "迁移后的 skill"
            root.mkdir()
            for folder in ["scripts", "assets", "examples"]:
                shutil.copytree(ROOT / folder, root / folder, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            cwd = work / "unrelated-cwd"
            cwd.mkdir()
            env = dict(os.environ, HOME=str(work / "home-does-not-exist"), PYTHONPATH="/does/not/exist", PYTHONDONTWRITEBYTECODE="1")
            self.assertFalse(Path(env["HOME"]).exists())
            output = cwd / "独立输出.html"
            markdown = cwd / "独立输出.md"
            self.run_cli(root, "render_report.py", root / "examples/demo-report.json", output, "--markdown", markdown, cwd=cwd, env=env)
            self.run_cli(root, "validate_report.py", root / "examples/demo-report.json", "--html", output, cwd=cwd, env=env)
            self.assertEqual(output.read_text(encoding="utf-8"), self.html)
            self.assertFalse(Path(env["HOME"]).exists())
            self.assertFalse(list(root.rglob("__pycache__")))
            self.assertFalse(list(root.rglob("*.pyc")))

    def test_zip_extract_and_isolated_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            archive = work / "resources.zip"
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
                for folder in ["scripts", "assets", "examples"]:
                    for path in sorted((ROOT / folder).rglob("*")):
                        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                            bundle.write(path, Path("company-deep-research") / path.relative_to(ROOT))
            extracted = work / "extracted"
            extracted.mkdir()
            with zipfile.ZipFile(archive) as bundle:
                self.assertIsNone(bundle.testzip())
                self.assertTrue(all(not n.startswith("/") and ".." not in Path(n).parts for n in bundle.namelist()))
                bundle.extractall(extracted)
            root = extracted / "company-deep-research"
            env = dict(os.environ, HOME=str(work / "missing-home"), PYTHONDONTWRITEBYTECODE="1")
            output = work / "from-zip.html"
            self.run_cli(root, "render_report.py", root / "examples/demo-report.json", output, cwd=work, env=env)
            self.run_cli(root, "validate_report.py", root / "examples/demo-report.json", "--html", output, cwd=work, env=env)
            self.assertEqual(output.read_text(encoding="utf-8"), self.html)
            self.assertFalse(list(root.rglob("__pycache__")))

    def test_only_standard_library_imports_and_no_pycache(self):
        import ast
        modules = set()
        for path in (ROOT / "scripts").glob("*.py"):
            if path.name == "example.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    modules.update(n.name.split(".")[0] for n in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    modules.add(node.module.split(".")[0])
        allowed = {"sys", "datetime", "html", "json", "math", "pathlib", "re", "urllib", "argparse", "report_core", "validate_report", "copy", "os", "shutil", "socket", "subprocess", "tempfile", "unittest", "zipfile", "ast"}
        self.assertLessEqual(modules, allowed)
        self.assertFalse(list((ROOT / "scripts").rglob("__pycache__")))
        self.assertFalse(list((ROOT / "scripts").rglob("*.pyc")))

    def test_python39_compatible_syntax(self):
        import ast
        for path in (ROOT / "scripts").glob("*.py"):
            with self.subTest(path=path.name):
                ast.parse(path.read_text(encoding="utf-8"), feature_version=(3, 9))

    def test_standard_six_questions_and_moved_components(self):
        expected = ["行业", "商业模式", "竞争", "估值", "财务", "四状态"]
        for section, topic in zip(self.report["sections"], expected):
            self.assertIn(topic, section["title"])
            self.assertIn(section["title"], self.html)
            self.assertIn(section["title"], self.markdown)
        business = self.report["sections"][1]
        self.assertTrue(any(b.get("title") == "模拟业务闭环：动作不能代替财务证据" for b in business["blocks"]))
        finance = self.report["sections"][4]
        self.assertIn(numeric_table(self.report), finance["blocks"])
        self.assertTrue(any(b.get("title") == "模拟收入结构：只比较同量纲金额" for b in finance["blocks"]))
        self.assertTrue(any(b.get("kind") == "bar" and any(v is None for s in b["series"] for v in s["values"]) for b in finance["blocks"] if b["type"] == "chart"))
        self.assertIn("独立", self.report["kpis"][5]["period"])
        self.assertNotIn("FY2025", self.report["kpis"][5]["period"])

    def test_industry_drivers_and_priceable_supply_demand_are_synthetic(self):
        section = self.report["sections"][0]
        tables = [b for b in section["blocks"] if b["type"] == "table"]
        self.assertEqual(len(tables), 2)
        self.assertIn("行业驱动", tables[0]["title"])
        self.assertIn("可计价品类供需", tables[1]["title"])
        for block in tables:
            self.assertIn("S4", block["sources"])
            self.assertTrue(block["period"])
            self.assertRegex(block["title"], "虚构|合成")
            self.assertIn("非", block["title"])
        for row in tables[1]["rows"]:
            self.assertEqual(row[1] - row[2], row[3])
        self.assertTrue(all(s["kind"] == "demo" and s["url"].startswith("demo://") for s in self.report["sources"]))
        self.assertIn(DEMO_NOTICE, json.dumps(section, ensure_ascii=False))
        self.assertIn("不与公司 FY 数据合并", tables[1]["period"])

    def test_competition_layers_and_nonconsensus_boundaries(self):
        competition, valuation = self.report["sections"][2:4]
        layer_table = next(b for b in competition["blocks"] if "分层颠覆检验表" in b.get("title", ""))
        self.assertEqual([row[0] for row in layer_table["rows"]], ["工具层", "平台层", "成果层"])
        self.assertTrue(any("竞争格局" in b.get("title", "") for b in competition["blocks"]))
        self.assertTrue(any(b.get("title") == "合成估值场景 — 非价格预测" for b in valuation["blocks"]))
        self.assertTrue(any("非共识假设对照" in b.get("title", "") for b in valuation["blocks"]))
        self.assertIn("不假称市场共识", json.dumps(valuation, ensure_ascii=False))
        self.assertIn("没有真实价格", json.dumps(valuation, ensure_ascii=False))

    def test_four_states_three_paths_watchlist_and_verdict_references(self):
        section = self.report["sections"][5]
        cards = next(b for b in section["blocks"] if b["type"] == "cards")
        labels = ["盈利兑现", "逆境反转", "估值压缩", "预期提高"]
        self.assertEqual([item["label"].split("：")[0] for item in cards["items"]], labels)
        self.assertEqual([item["label"] for item in self.report["verdicts"]], labels)
        for verdict, reference in zip(self.report["verdicts"], ["第五问", "第五问", "第四问", "第六问"]):
            self.assertIn(reference, verdict["detail"])
        paths = next(b for b in section["blocks"] if "三路径综合表" in b.get("title", ""))
        self.assertEqual([row[0] for row in paths["rows"]], ["改善路径", "延续路径", "恶化路径"])
        watchlist = next(b for b in section["blocks"] if "六问跟踪清单" in b.get("title", ""))
        self.assertEqual(len(watchlist["rows"]), 6)
        empty_chart = next(b for b in section["blocks"] if b["type"] == "chart")
        self.assertTrue(all(v is None for s in empty_chart["series"] for v in s["values"]))
        self.assertIn("全序列缺数据", self.html)
        self.assertIn(DEMO_NOTICE, json.dumps(section, ensure_ascii=False))

    def test_anchor_javascript_behavior_offline_with_webview_failures(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("环境没有 node，无法执行 JS 行为测试；原生锚点仍保留")
        parser = PageParser()
        parser.feed(self.html)
        anchors = [attrs["href"] for tag, attrs in parser.tags if tag == "a" and attrs.get("href", "").startswith("#")]
        first_chart = next(identity for identity in parser.id_counts if identity.endswith("-tab-chart"))
        prefix = first_chart[:-len("-tab-chart")]
        payload = {"script": parser.scripts[0], "ids": list(parser.id_counts), "anchors": anchors, "prefix": prefix}
        # Node 的 vm 和 assert 都是内置模块；用离线 DOM 替身执行实际内联脚本。
        harness = r'''
const assert = require('node:assert/strict');
const vm = require('node:vm');
let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', function (part) { input += part; });
process.stdin.on('end', function () {
  const data = JSON.parse(input);
  function setup(historyBlocked) {
    const nodes = {};
    const clicks = [];
    const scrolls = [];
    const replacements = [];
    const tabHandlers = {};
    const win = {pageYOffset: 75};
    const doc = {documentElement: {scrollTop: 0}};
    data.ids.forEach(function (id, index) {
      nodes[id] = {top: 200 + index * 50, hidden: false};
      nodes[id].getBoundingClientRect = function () {
        return {top: this.top - (win.pageYOffset || doc.documentElement.scrollTop || 0)};
      };
    });
    win.scrollTo = function (x, y) { scrolls.push([x, y]); win.pageYOffset = y; };
    win.history = {replaceState: function (state, title, hash) {
      if (historyBlocked) throw new Error('WebView history blocked');
      replacements.push(hash);
    }};
    const buttons = ['chart', 'table'].map(function (view) {
      const attrs = {'aria-controls': data.prefix + '-' + view};
      return {
        getAttribute: function (key) { return attrs[key]; },
        setAttribute: function (key, value) { attrs[key] = value; },
        focus: function () { this.focused = true; },
        closest: function () { return card; }
      };
    });
    const tabs = {
      hidden: true,
      addEventListener: function (kind, handler) { tabHandlers[kind] = handler; },
      querySelector: function () { return buttons[0]; }
    };
    const card = {
      querySelector: function () { return tabs; },
      querySelectorAll: function () { return buttons; }
    };
    doc.getElementById = function (id) { return nodes[id] || null; };
    doc.querySelectorAll = function () { return [card]; };
    doc.addEventListener = function (kind, handler) { if (kind === 'click') clicks.push(handler); };
    vm.runInNewContext(data.script, {window: win, document: doc});
    assert.equal(tabs.hidden, false);
    assert.equal(nodes[data.prefix + '-table'].hidden, true);
    function click(hash, options) {
      options = options || {};
      const link = {
        getAttribute: function (key) { return key === 'href' ? hash : options.linkTarget || null; },
        hasAttribute: function () { return Boolean(options.download); }
      };
      const event = Object.assign({
        button: 0, defaultPrevented: false,
        target: {closest: function () { return link; }},
        preventDefault: function () { this.defaultPrevented = true; }
      }, options);
      clicks.forEach(function (handler) { handler(event); });
      return event;
    }
    return {win, doc, nodes, clicks, click, scrolls, replacements, buttons, tabHandlers};
  }
  [false, true].forEach(function (blocked) {
    const state = setup(blocked);
    data.anchors.forEach(function (hash) {
      const event = state.click(hash);
      assert.equal(event.defaultPrevented, true);
      assert.deepEqual(state.scrolls[state.scrolls.length - 1], [0, Math.max(0, state.nodes[hash.slice(1)].top - 20)]);
    });
    const beforeRepeat = state.scrolls.length;
    state.click('#q1');
    state.click('#q1');
    assert.equal(state.scrolls.length, beforeRepeat + 2);
    assert.equal(state.replacements.length, blocked ? 0 : state.scrolls.length);
    const count = state.scrolls.length;
    const ignored = [
      ['#q2', {ctrlKey: true}], ['#q2', {metaKey: true}],
      ['#q2', {shiftKey: true}], ['#q2', {altKey: true}],
      ['#q2', {button: 1}], ['#q2', {button: 2}],
      ['#q2', {linkTarget: '_blank'}], ['#q2', {download: true}],
      ['#missing', {}], ['#中文', {}], ['#q1%22', {}],
      ['javascript:alert(1)', {}], ['https://example.invalid/#q2', {}],
      ['#q2', {target: null}], ['#q2', {defaultPrevented: true}]
    ];
    ignored.forEach(function (item) {
      const event = state.click(item[0], item[1]);
      assert.equal(event.defaultPrevented, Boolean(item[1].defaultPrevented));
    });
    assert.equal(state.scrolls.length, count);
    state.win.pageYOffset = undefined;
    state.doc.documentElement.scrollTop = 80;
    state.click('#q2');
    assert.equal(state.scrolls[state.scrolls.length - 1][1], state.nodes.q2.top - 20);
    state.nodes.q1.top = 5;
    state.click('#q1');
    assert.equal(state.scrolls[state.scrolls.length - 1][1], 0);
    const successCount = state.scrolls.length;
    state.win.scrollTo = function () { throw new Error('scroll unavailable'); };
    assert.equal(state.click('#q1').defaultPrevented, false);
    state.win.scrollTo = undefined;
    assert.equal(state.click('#q2').defaultPrevented, false);
    assert.equal(state.scrolls.length, successCount);
    // history 失败不影响独立的图表切换和键盘标签操作。
    state.tabHandlers.click({target: {closest: function () { return state.buttons[1]; }}});
    assert.equal(state.nodes[data.prefix + '-chart'].hidden, true);
    assert.equal(state.nodes[data.prefix + '-table'].hidden, false);
    const keyEvent = {key: 'Home', target: {closest: function () { return state.buttons[1]; }}, preventDefault: function () { this.prevented = true; }};
    state.tabHandlers.keydown(keyEvent);
    assert.equal(keyEvent.prevented, true);
    assert.equal(state.buttons[0].focused, true);
    assert.equal(state.nodes[data.prefix + '-chart'].hidden, false);
  });
});
'''
        result = subprocess.run([node, "-e", harness], input=json.dumps(payload, ensure_ascii=False), capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_inline_javascript_node_check_when_available(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("环境没有 node；SVG／表格仍可离线阅读")
        parser = PageParser()
        parser.feed(self.html)
        self.assertEqual(len(parser.scripts), 1)
        result = subprocess.run([node, "--check"], input=parser.scripts[0], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
