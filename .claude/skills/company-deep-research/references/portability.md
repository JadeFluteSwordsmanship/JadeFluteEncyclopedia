# 可移植性与依赖清单

## 保证的边界

把company-deep-research整个目录复制到任意机器；拥有Python3.9以上即可执行渲染、校验和测试。无需Python第三方包、Node、npm、浏览器、字体下载、CDN、PDF模块、用户家目录或宿主金融技能。脚本用自身__file__解析资源，支持不同工作目录与带空格／中文路径。

实时深研仍需要能读取资料并进行推理的模型／执行器与联网或用户提供材料。这里打包的是全部核心方法、模板和工具，不是把某平台云搜索、数据授权和模型服务复制进仓库。金融插件或搜索服务缺失时走公开一手来源；无联网不假装获得最新行情。

## 目录契约

- SKILL.md：跨执行器入口和六问流程。
- references/：研究法、市场与来源、估值财务、内容模板、schema、设计、来源和迁移说明。
- scripts/report_core.py：标准库schema／安全渲染／SVG／Markdown。
- scripts/render_report.py、validate_report.py：命令行入口。
- scripts/test_skill.py：标准库unittest，包含移到独立目录、空HOME、不同cwd及隔离模式执行。
- assets/report.css、report.js：输出时内联，不要求旁边放静态文件。
- examples/：显著标记的虚构示例JSON／HTML／Markdown。

没有额外vendored第三方库，因核心不用第三方库；没有调用workbuddy-finance-skill或a-share-deep-dive的运行依赖。六问、财务估值和HTML规范已在references内重新写成完整独立方法。

## 在仓库内使用

规范来源是.claude/skills/company-deep-research。Cursor和WorkBuddy的项目skills目录通过相对软链接指向.claude/skills，避免三份维护分叉。各IDE对技能扫描、加载和刷新机制不同，不能仅据文件存在就宣称已在当前会话注册；必要时重新打开项目或显式读取SKILL.md。

Claude使用仓库根CLAUDE.md薄入口，其他执行器可读AGENTS.md；独立复制本技能时不需要任何项目规则。不要把本项目自动发群、Git推送等约定嵌入核心执行步骤。

Windows检出若不恢复符号链接，可直接从.claude/skills加载，或把整个技能目录复制到该IDE项目skills目录；不需要创建系统级链接或硬编码作者机器。发布zip时保持目录结构，Python命令可按环境使用python而非python3，不使用Unix专有渲染依赖。

## 验证命令

将SKILL_DIR替换为实际技能目录；输出父目录须先存在。

```bash
python3 "$SKILL_DIR/scripts/test_skill.py"
python3 "$SKILL_DIR/scripts/render_report.py" "$SKILL_DIR/examples/demo-report.json" "demo.html" --markdown "demo.md"
python3 "$SKILL_DIR/scripts/validate_report.py" "$SKILL_DIR/examples/demo-report.json" --html "demo.html"
```

可选开发检查：node --check assets/report.js。Python测试可使用-I隔离执行，不依赖PYTHONPATH。测试合成数据不用于投资，也不证明任何真实证券数据正确。

## 分发

直接Git检出即可。分发zip包含整个技能目录，不放绝对软链接、密钥、虚拟环境、缓存或平台账户。zip包是本次版本快照，后续修改源文件需重新打包。可用Python标准库zipfile手工打包；已有宿主打包器只用于开发交付，本技能运行不调用它。

## 不承诺的能力

不自带全市场抓取、无需鉴权的商业数据库、自动登录或云搜索额度；不执行交易；不导出PDF／Word；不保证每个模型同等深度；不要求自动化发群或部署。若未来增加可选金融适配器，须明确授权、依赖版本、覆盖、失败降级，不改变本技能的公开资料核心链路。
