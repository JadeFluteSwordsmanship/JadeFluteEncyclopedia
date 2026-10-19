# 自下而上（westock）

命令细节以 `.cursor/skills/westock-data/SKILL.md` 为准。这里是交易研究的**最小取数单**。同业筛选用 `.cursor/skills/westock-tool/SKILL.md`。

代码格式：`sh600000` / `sz000001` / `hk00700` / `usAAPL`。先 `search` 再查。

## 必跑

```bash
westock-data search <名称或ticker>
westock-data quote <code>
westock-data profile <code>
westock-data finance <code> --num 4
westock-data kline <code> --period day --limit 120
westock-data news <code> --limit 15 --type 3
```

美股利润表：`finance usXXXX --type income --num 4`。港股：`zhsy`。A 股：默认三张表，需要时 `--type lrb`。

## 按市场补跑

**A 股**

```bash
westock-data chip <code>
westock-data asfund <code>
westock-data technical <code> --group macd,rsi,ma
westock-data risk <code>
westock-data shareholder <code>
westock-data consensus <code>
westock-data rating <code>
westock-data reserve <code>
```

**港股**：`hkfund`、`shareholder`、`rating`。  
**美股**：`usfund`（卖空）、`rating`。

## 同业

```bash
westock-data search <行业> --sector
westock-data sector --search <行业>
westock-tool filter "intersect([PE_TTM > 0, PE_TTM < 80])" --universe <板块代码> --orderby PE_TTM:asc
```

港股/美股字段名不同，见 westock-tool 说明，禁止把 A 股字段套到 `--market us`。

## 必须写进备忘录的量

| 块 | 至少回答 |
|----|----------|
| 利润 | 最近 4 期收入、利润、毛利率；有没有一次性；FCF 是否为负 |
| 估值 | 现价、市值、PE/PB/PS；相对自身 52 周和同业 |
| 空间 | 乐观/基准/悲观下利润或收入 × 合理倍数，得出市值区间，不要点估计 |
| 筹码量能 | A 股：平均成本、获利盘、换手、主力净流入。美股：成交量相对均量、卖空若有 |
| 预期差 | 一致预期是否在上修/下修；最近一次财报后共识怎么变 |

## 红旗（看见就要写进风险）

- 增发 / ATM / 换股领口导致稀释
- 商誉、应收账款、存货异常
- 质押、解禁、诉讼（A 股 `risk`）
- 利润靠补贴或资产处置
- 市销率/市盈率相对同业极端，且分子还没出现

货币：美股用美元，港股用港元或美元（跟数据走），禁止把人民币符号套到外币报表。
