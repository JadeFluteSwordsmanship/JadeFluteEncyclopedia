# 横纵报告网页阅读页 · 设计规范

网页 HTML 是给屏幕阅读的交付物，和 PDF 的 A4 印刷页不是同一套样式。所有报告走 `scripts/md_to_html.py` + `references/web-report.html`，不要为单篇报告手写 CSS。

**已审定（2026-10-13，深度研究）：** 本模板作为默认网页阅读页。后续报告按此生成，不要另起视觉方案。

## Design Read

Reading this as: editorial long-form research report for analysts, with a quiet publication language, leaning toward native CSS + JadeFlute ink/celadon identity.

这是长文阅读页，不是落地页、不是仪表盘。不要套 SaaS hero / 三列功能卡 / 信任 logo 墙。

## Dials

| Dial | Value | 原因 |
|------|-------|------|
| DESIGN_VARIANCE | 6 | 编辑向、有偏移，但不做实验性乱排 |
| MOTION_INTENSITY | 4 | 进度条、目录高亮、主题切换；不做滚屏劫持 |
| VISUAL_DENSITY | 4 | 正文要能读完 1–3 万字，留白服务于阅读而不是展览 |

## 品牌与调色

玉笛百科：墨蓝底、玉色强调。网页侧去掉 PDF 封面那路暖金/米纸，避免做成「beige + brass」工艺品风。

**浅色（默认阅读）**

- 纸色 `--paper: #f2f5f3`（冷白，不是奶油纸）
- 墨色 `--ink: #15232c`
- 玉色 `--jade: #2f7a64`（饱和度压住，只作强调）
- 辅助 `--muted: #4a5c61`、`--hair: #cdd8d3`

**深色**

- `--paper: #12181a` / `--ink: #e4ece8` / `--jade: #6eb89f`

封面允许一次 Color Block：浅色模式下封面永远是墨底浅字，进入正文后锁在纸色。深色模式下封面与正文同一套暗色，不再二次翻转。

圆角只准一种：控件与卡片 `8px`。不要混用胶囊按钮 + 大方卡。

## 排版

- 中文：系统黑体栈 `PingFang SC / Hiragino Sans GB / Noto Sans SC / Microsoft YaHei`
- 不要 Inter，不要 Fraunces / Instrument Serif
- 正文字号默认 17px，行距 1.85，栏宽约 `42rem` / `65ch`
- 中文不用斜体装饰；引用靠左边玉线，不靠 italic
- UI 文案禁止 em-dash（`—` / `–`）；正文来自 Markdown，转换器不改写研究报告原文

## 信息架构（固定）

1. 顶栏：品牌、当前标题、目录、字号、主题
2. 封面：对象名 + 副标题 + 元信息 + 字数/阅读时间（底对齐，不要居中海报）
3. 主体：桌面左侧粘滞目录 + 右侧正文；移动端目录为抽屉
4. 「核心结论速览 / 一句话定义」做成开篇结论带，不是普通 h2
5. 「剧本」小节做成三种色温卡片（乐观 / 基准 / 风险），布局仍是单栏，不是三列均分功能卡
6. 表格外层横滑，表头墨底，行间只保留底边
7. 来源区降字号、链接可点
8. 页脚：玉笛百科 + 横纵分析法，不要版本号

## 动效与状态

- 阅读进度条（顶，玉色）
- 目录 IntersectionObserver 高亮
- 顶栏滚过封面后实底
- `prefers-reduced-motion: reduce` 时停掉过渡
- 深浅色、字号写入 `localStorage`
- 焦点可见：`outline: 2px solid var(--jade)`
- 对比度：正文与大标题达到 WCAG AA；按钮文字不得浅底浅字

## 明确禁止

- 紫雾、霓虹描边、玻璃拟态堆叠、三列等宽功能卡
- 每个小节都加 uppercase tracking 眉题
- 封面里塞徽章、假数据、Scroll 提示
- 为装饰生成游戏截图或手绘 SVG 插画
- 把 PDF 的 `@page` / A4 边距直接搬到网页

改视觉只改 `web-report.html` 这一份模板，然后用完美世界或任意一篇报告重新生成验收。
