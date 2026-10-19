# 宏观过滤器（行业 best practice）

先体制，后行业，最后才是股票。本页规定**顺序和数据从哪来**，不规定当前点位。

## 必走顺序

1. **全球流动性**：美元流动性、美债发行与 QT/QE 叙事、中国社融/M1/M2。
2. **美债实际利率**：名义 10Y − 通胀预期，或 TIPS 实际利率。没有原值时，用 `usTLT.OQ` 方向作代理，并注明是代理。
3. **美日欧货币政策**：Fed / BOJ / ECB 利率路径和点阵/纪要，不是「感觉偏鹰」。
4. **美元**：优先 DXY 原值（FRED `DTWEXBGS` 或公开行情）；westock 代理 `usUUP.AM`（Invesco 美元 ETF）、反向 `usUDN.AM`。
5. **总需求 / 总供给**：增长（GDP、PMI、工业）对通胀（CPI/PCE/PPI）。分清需求拉动还是供给冲击（关税、能源、战争）。
6. **各国政策**：财政、产业补贴、地产、消费。中国用 westock 宏观；美国用日历和一手文件。
7. **中观对接**：这个体制打在该股的哪个因子上。

## westock（中国与代理）

先读 `.cursor/skills/westock-data/SKILL.md`。

```bash
westock-data macro core_indicatros_cur
westock-data macro gdp,cpi_ppi,pmi,financing,fundquantity,fundcost
westock-data calendar --country 2 --indicator 1   # 美国经济
westock-data calendar --country 2 --indicator 2   # 美国央行
westock-data quote usUUP.AM,usTLT.OQ,usGLD.AM,usUSO.AM,us.INX,us.IXIC,sh000001
```

`fundcost` 是中国回购/Shibor，**不要**写成美国联邦基金。`fundquantity` 是中国货币数量。

## 必须联网的一手（westock 覆盖不到）

| 对象 | 优先来源 |
|------|----------|
| FOMC 点阵、纪要、讲话 | federalreserve.gov |
| 美国实际利率、DXY、10Y | FRED、Treasury |
| BOJ / ECB | 各自官网新闻稿 |
| 关税、出口管制 | USTR、商务部、中国官方公报 |

`WebSearch` 发现 URL，`WebFetch` 读原文。转述媒体只作线索。

## 闸门怎么打

对**这个标的的因子暴露**打灯，不是对「大盘好不好」打灯。

| 灯 | 含义 | 仓位含义 |
|----|------|----------|
| 绿 | 体制对该因子中性或友好，且未被拥挤交易透支 | 才允许讨论中高仓 |
| 黄 | 有逆风但价格已部分反映，或逆风来自可对冲的单一因子 | 可做，仓位打折 |
| 红 | 系统性估值压缩正在打这个因子，又没有 90 天特异性催化 | 观望或极小仓战术 |

长久期亏损成长股在加息/实际利率上行期，默认偏红，除非合同/产品节点能在 90 天内改分子。出口链在美元过强或关税升级期，默认偏黄或红。

## 写进报告的最小集合

- 一句话体制（增长 × 通胀 × 流动性）
- 实际利率或 TLT 方向、美元方向
- 对该股的灯色和因子
- 2–4 个带来源的数字
