# Report JSON v1

使用UTF-8标准JSON；禁止NaN、Infinity、重复键和未定义字段。顶层所有字段必需，不接受任意HTML或Markdown注入。`examples/demo-report.json`是完整可执行样本，数字全部虚构，不能用于真实公司。

## 顶层

| 字段 | 类型与约束 |
| --- | --- |
| schema_version | 整数1 |
| title、company、subtitle、as_of、thesis | 非空字符串；as_of明确行情session、财报期、来源时点和币种口径 |
| ticker | A股六位、港股五位、美股大写ticker，可带点／短线类别后缀 |
| market | A股／港股／美股 |
| report_date | 有效YYYY-MM-DD，实际研究日 |
| mode | research／draft／demo；research至少一个primary来源，draft为资料不足骨架、允许零来源；research和draft均禁止demo来源 |
| summary | 非空字符串数组；观点依据在六章给出 |
| verdicts | 四对象依次label为盈利兑现、逆境反转、估值压缩、预期提高；各含status、detail、tone |
| kpis | 零至六对象；各含label、value、note、sources、period |
| sections | 恰好六对象，id依次q1至q6，title非空、blocks非空数组 |
| sources | 来源对象数组，ID唯一；research／demo非空，draft允许为空 |

`value`可为非空文字或有限数字；文字数字须带单位。缺项卡用“暂缺”并解释，不省略source和period字段，可引用证实未披露的原始材料。tone为neutral、primary、risk、positive：primary强调主观点，risk提示风险，positive用中国市场红色；不表示概率。

## 来源对象

包含 `id`（S1、S2…）、`title`、`url`、`publisher`、`published_at`、`accessed_at`、`kind`。日期允许YYYY-MM-DD或带时区的ISO时间戳，时间戳需秒。kind是primary、secondary、assumption、demo。URL必须真实可访问http／https，无用户名、密码或脚本；demo模式的demo来源可用demo://标识，不变成可访问公告。

来源日期缺失的处理见data-and-markets.md，不能捏造披露日。数字分块用period表达实际统计期，published_at表达资料发布，不混同。

## 内容块

各块必有 `type`；允许可选 `sources` 数组，引用必须存在且不重复。数字表、chart和KPI必须有引用与period。无来源的定性概念也需研究者人工核实其适用性。

| type | 其他必需字段 | 可选字段 |
| --- | --- | --- |
| paragraph | text | sources |
| heading | text | sources |
| callout | text、tone | sources |
| bullets | items：非空字符串数组 | sources |
| table | title、columns：字符串数组、rows：矩形二维数组 | sources、period、basis |
| chart | title、categories、series、unit、period | sources（实际必需）、kind：line或bar |
| flow | title、steps：非空字符串数组 | sources |
| cards | items：非空数组，各含label、text、tone | sources |

表格cell允许非空文字、有限数字、null；null显示“缺数据”，不转换零。数字写成文字也要来源与period。basis写公式、单位、模型假设及不同来源行的对应关系。

chart.series每项仅name与values数组，长度与categories一致；值是有限数字或null，不接受bool、序列级单位或双轴。同一图unit共享，不同量纲分图；语义单位一致由研究者复核。null断线／不画柱；全空序列显式显示缺数据。

## 一个图表块示例

```json
{
  "type": "chart",
  "kind": "line",
  "title": "核心利润趋势",
  "categories": ["FY2023", "FY2024", "FY2025"],
  "series": [{"name": "核心经营利润", "values": [-3, null, 2]}],
  "unit": "金额单位在正式研究中按财报填入",
  "period": "示范年度窗口，数字仅示意字段结构",
  "sources": ["S1"]
}
```

上例只是schema教学，不是财务事实，不复制到真实报告。正式数据填完先执行validate_report，再render_report，再验证HTML一致性。修改HTML不能替代修改JSON；生成器会拒绝与输入不一致的成品。

## 资料不足的draft

使用 `mode=draft` 交付缺口骨架，HTML与Markdown醒目显示“资料不足／研究骨架，尚未完成公司深度研究”。允许sources和kpis为空，仍保留六章、四状态卡，状态注明证据不足；仅有二手资料也可引用，但不伪造primary。draft无来源时只写定性缺口与研究问题，不生成无来源数字图。所有有数字的表格／chart／KPI仍受来源与period约束。不要把draft称为正式公司研究；合成演示只允许demo。

## 校验边界

自动检查结构、代码格式、日期、来源ID、URL安全、数组对齐、有限数字、图表缺值、外链资产及HTML一致性；不能识别所有造假、前视偏差、财年错配、虚假共识或单位语义。`research`有一个primary来源通过结构门槛，不代表达到深研证据门槛；人工按六问质检覆盖与反证。
