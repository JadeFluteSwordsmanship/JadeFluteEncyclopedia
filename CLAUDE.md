# 玉笛百科执行入口

读取仓库根 `AGENTS.md`，遵循目录、研究分流与项目交付约定。技能规范来源统一为 `.claude/skills/`；`.cursor/skills` 和 `.workbuddy/skills` 是指向此目录的相对软链接。

- A股／港股／美股公司分析、六问深研、SDGR参考风格：读取 `.claude/skills/company-deep-research/SKILL.md`，使用本技能自己的JSON到HTML／Markdown链路，不要求其他金融skill。
- 明确横纵历史研究：`hv-analysis`。
- 买卖点、仓位、是否投入资金：`trade-research`。
- 非单公司宏观／行业时点：`macro-research`。

公司深研的核心方法、模板与标准库工具全部位于该技能目录，独立复制后不需要本项目入口或特定IDE；所在项目的提交推送、上传和发群属于独立交付层，不是技能生成能力的运行依赖。
