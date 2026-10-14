# Decisions API：软件要的是判断，混元还停在写字

> 研究时间：2026年10月14日
> 所属领域：AI 应用软件 / 决策模型 / 模型网关
> 研究对象类型：概念（协议与产品族）兼内部接入层
> 研究员：玉笛百科
> 研究方法：纵向历史溯源 + 横向竞品对比 + 交汇洞察

## 核心结论速览

**一句话定义**：Decisions API 是一条「不写字、只做有界判断」的专用接口：应用提交一段状态加一组类型化问题，模型返回概率、选项或量表，程序拿回来就能进 `if`。OpenAI 在 2026 年 10 月 6 日把它做成 `POST /v1/decisions`；混元（hy）截至 10 月 14 日公开文档里没有对等端点。司内口语里的 tt-switch，公网证据指向 Claude Code / Codex 一类工具的供应商切换器（CC Switch / TT switch），它切的是聊天协议，接不住一条还不存在的混元 Decisions。

**关键判断**：

1. 论坛问「hy 什么时候可以出 Decisions API」，问的是混元有没有一条和 OpenAI / Jev 同构的决策通道。公开事实停在这里：TokenHub 2026 年 10 月 13 日的 API 说明只列 Chat Completions、Responses、Anthropic Messages 和 `GET /v1/models`，模型表是 `hy3`、`hy4-preview`、DeepSeek、GLM、Kimi。分类决策在腾讯云上已经有一个槽位，但不在混元身上：模型路由 CMR 同一天更新的调度文档，把「分类决策模型（如 Jev 模型）」写成可选模态，意图路由可以「开启分类决策模型」。槽有了，混元自研决策模型还没有。
2. 这种 API 的主场是工作流和 Agent 套件外侧的闸门，不是 Cursor 对话里再冒出一个 MCP 工具。OpenAI 官方把密钥留在服务端，语音场景走 Live API 的 client-delegation：模型继续说话，应用在旁边调 Decisions、执行动作、把结果塞回去。Jev 社区把同一层做成 Claude Code 的 `PreToolUse` hook 和 Cursor 的 `beforeShellExecution`，主模型一 token 都不用花。MCP（`jev_decide`）可以嵌进对话，那是给 Agent「想起来再问」用的慢路径。Cursor 没有把 OpenAI `/v1/decisions` 做成内置工具，公网也查不到。
3. 「看 OpenAI 和其他厂商的接入速度，应该很容易吧？」协议层确实快。阿里云百炼已经提供 `POST /compatible-mode/v1/systemone`，模型 `decision-model-preview`，官方示例返回 `latency_ms: 52.9`，文档页更新到 2026 年 10 月 11 日。微软 10 月 9 日发布 Microsoft-Decision-1，价签对齐 Jev 的 0.042 美元/百万输入。Cloudflare Clef 更早，10 月 1 日。真正没出独立端点的是 Anthropic、Gemini、DeepSeek、Kimi 和混元。网关转发 Jev 或 Luna 是几天的活；训一套校准过的混元决策头、再让 tt-switch 多一种协议，是两件难度完全不同的事。后者容易，前者才是论坛在等的东西。

**机会与风险**：

- 机会：内部工具要「简单快速的意图判断」，今天就能用三条现成路：CMR 意图路由挂 Jev、TokenHub 上 `hy3` 的 `json_schema` 凑合分类、或直连 OpenAI Decisions / 百炼 systemone。tt-switch 一旦多一种 Decisions 协议，Claude Code 热路径上的模型选择和工具闸门可以同时变便宜。
- 风险：把 `hy3` 结构化输出当成 Decisions，延迟和校准都还在生成模型那一档。把 MCP 当成主接入方式，等于让会写字的模型决定要不要做判断，判断层的速度优势会被吃掉。混元若只抄接口、不抄校准，上线日会很快，可用性会很差。

---

## 一、纵向分析：从诞生到当下

> **叙事主线**：软件一直需要一种模糊的 `if`。行业先把判断塞进聊天模型，再发现聊天模型会写字、会幻觉、会按 token 收费。有人做出不会写字的决策模型，实验室和云厂商在四周内把同一套协议铺开。混元还停在「会写 JSON 的快模型」，tt-switch 还停在「切换谁来写字」。

### 1.1 起源：判断一直在，接口一直错位（2022–2025）

客服工单该去哪个组、这条请求要不要调工具、这段补丁过不过测试，这些判断每天发生成千上万次。2018 年以后，固定标签分类器用 BERT 一类模型就能做，标签集在训练时冻死，场景一变就要重训。

2022 年 8 月 10 日，OpenAI 上线 Moderation API。它是 GPT 系分类器，免费，输出一组有害内容类别的分数。用途很窄：内容审核，不是任意业务 schema。

真正把「判断」送进应用开发者手里的，是 2023 年 6 月 13 日的 Function calling。`gpt-4-0613` 和 `gpt-3.5-turbo-0613` 可以输出 JSON 函数参数。模型仍在写字，只是字被规定成参数。2023 年 11 月的 JSON mode 保证合法 JSON，不保证字段对。2024 年 8 月 6 日 Structured Outputs 把 `strict: true` 写进 API，JSON Schema 被语法约束住。

这一串升级解决了「解析失败」。没有解决「每次判断都要生成」。模型会在心里拟一篇分析，再把分析压成字段。延迟按秒计，输出按 token 加价，说出来的 95% 把握对不上长期正确率。Agent 一流行，这个错位被放大。一次能改仓库、开浏览器、跑测试的任务里，微型判断可能有几十上百次：现在该不该搜、这条结果还要不要、用户是在追问还是开新任务。每一问都请 Claude 或 GPT 想一遍，账单和尾延迟会先把产品杀死。

2025 年 10 月 9 日，arxiv 上出现 *When to Reason: Semantic Router for vLLM*（2510.08731）。它做的是「这条请求要不要走推理」，在 MMLU-Pro 上宣称准确率加 10.2 个百分点、延迟降 47.1%、token 降 48.5%。2026 年 2 月的技术报告把路由写成 13 类信号加布尔决策引擎。这些工作服务的仍是 chat completions：分类器站在大模型门口，大模型继续写字。缺的是把分类器自己做成一种一等 API。

内部工具链其实早就在用土办法填这个缺口。规则：关键词命中就走某个模型。小模型：用 7B、8B 先做一次分类，再把标签塞进路由表。Prompt：在系统提示词里写「只输出 billing 或 technical」。三条路都能跑，也一直在跑。规则太脆，同义词一变就漏。小模型要为每个标签集准备数据。Prompt 最灵活，也最贵最慢，输出偶发飘出 schema。论坛说「蛮多工具可以通过简单快速的意图判断猛猛提效」，指的是把这三条土办法收成一条稳定 API。土办法的存在，说明需求不是新的；独立端点的出现，说明旧接口已经劝退了足够多的人。

### 1.2 品类被命名：Jev 把 System One 做成函数（2026 年 9 月）

2026 年 9 月 15 日，TypeSafe AI 把 Jev 放进 early access。创始人 Diogo Almeida 是 InstructGPT / RLHF 论文的共同作者。官宣博客把产品写成 frontier-intelligence function call：非结构化状态进，带类型的概率决策出。官网第一句更硬：We took the opposite research direction。

接口形状后来被所有人抄走。一次请求是 `state` 加一组 `questions`。输出只有三种原语：Choice（从给定选项里选一个）、Score（在有序刻度上打分）、Noul（某事是否成立，返回 0 到 1 的概率）。模型不生成文本。官方定价每百万输入 token 0.042 美元，输出免费；端到端延迟写 70 到 500 毫秒。训练方法自称 Reinforcement Learning for Calibrated Decisions（RLCD）：模型说 90% 把握，在代表性样本上大约应该对九成。文档自己写了限制：校准是在一组预测上度量的，不保证单条正确。「can't hallucinate」保证的是类型，不是真相。

同一周，开发者开始把它塞进三个位置。模型路由：闲聊走小模型，写代码走贵模型。工具门槛：先问现在需不需要工具，再在锁死的工具名里选。验证与监督：大模型写完补丁，外面站一个不写评语、只打分的裁判。Agent 的骨架从「全程 LLM」变成「规则 + 决策模型 + LLM + 工具」。

Jev 还给 Agent 工具链留了门。jevmodel.org 提供远程 MCP，工具名 `jev_decide` / `jev_noul` / `jev_choice` / `jev_score`，文档写明面向 Claude Code、Cursor、Cline。这条路径后来常被误读成「Decisions 就是 MCP」。它只是 Jev 的一种封装。官方设计仍然是应用自己 `POST /v1/systemone`。

社区把同一层又往下凿了一格。有人在 Claude Code 清上下文：终端输出和工具结果先交给 Jev 打分，只把仍与当前任务相关的片段留给大模型。有人拿 Agent 执行记录问它：目标完成了没有、有没有漏项。有人用它在几十秒里拆几百条广告。这些用法有一个共同点：判断发生在主模型的上下文预算之外。主模型越贵，这一刀越值得。混元论坛里「简单快速的意图判断猛猛提效」，指的就是这一刀，不是再让 `hy3` 多写一段分析。

### 1.3 实验室把品类收进自己的栈（2026 年 9 月 22 日–10 月 6 日）

2026 年 9 月 22 日，OpenAI changelog 发布 GPT-6 Sol 和 GPT-6 Luna，当时它们是生成模型。Luna 走 Responses API 时，输入 0.10 美元/百万 token，输出 0.50 美元，支持 function calling、structured outputs、streaming、prompt caching。

7 天后的 DevDay（9 月 29 日），Decisions API 以 limited preview 亮相。官方 recap 写它会在 coming days 做更广的 release。

10 月 6 日，公开 beta。社区帖创建于 UTC 20:53。changelog 同日。Python SDK PR #4033 20:50 开、21:09 合，发布进 v3.26.0；Node PR #2886 合进 7.30.0。官方指南把产品写成一句话：

> The Decisions API evaluates text, images, or both and returns typed answers about 10x faster than the Responses API.

端点是 `POST https://api.openai.com/v1/decisions`。模型目前只有 `gpt-6-luna`。请求三块：`model`、`input`（文本或带 inline base64 图的 user 消息）、`questions`。输出三种：`predicate`（条件为真的概率）、`choice`（固定选项）、`score`（有序量表的概率加权平均）。另外还有 `refusal`。定价：Luna 走 Decisions 时只收输入 0.10 美元/百万 token，不收 cache-read、cache-write、output。官方明确对比：需要自定义 JSON 对象或 tool arguments 时，仍用 Responses；需要这三种答案时，才用 Decisions。

OpenAI 没有宣称新架构或 RLCD。它给已经会聊天的 Luna 开了一条更快的决策通道。社区立刻拿它和 Jev 比。有人测图像输入在约 3 Mbps 网上大约 0.8 秒；有人在几百题小样本里看到 Jev 中位约 0.3 秒、Luna 约 1.6 秒。有人发现 predicate 校准较好，choice 会把 70% 的硬币压成 98% heads。这些是社区实验，不是官方 SLA。官方毫秒级延迟、独立 API Reference schema、GA 日期，截至本调研仍暂缺。指南只说 expect to GA in the coming weeks。

语音是 OpenAI 相对 Jev 的差异化。文档 *Connect voice to Decisions* 规定 client-delegation：GPT-Live 继续说和听，应用在 `session.delegation.created` 之后自己调 Decisions，执行 `back` / `reload` / `noop` 这类动作，再用 `session.commentary.append` 让 Live 开口汇报。复杂请求可以把 `reason` 做成一个 choice，再转 Responses 上的推理模型。Luna 模型卡写明 Live 本身 Not supported。语音会话是 GPT-Live，Decisions 是应用在 delegation 窗口里的侧路调用。

### 1.4 四周竞赛：开源、云厂商、中国云（2026 年 10 月）

窗口被挤满的速度，比混元论坛里的等待更说明问题。

10 月 1 日，Cloudflare 发布 Clef / Clef-flash，Apache-2.0，挂在 Workers AI，API 按 Jev 的 System One 形状兼容。骨干冻结 Qwen，推理只做 prefill，再对合法 schema 并行打分。厂商 43-eval 表上，Clef 中位 209.3 毫秒，Clef-flash 38.8 毫秒，同表 Jev 524.1 毫秒。changelog 把 Agent guardrails 写成「调工具前几十毫秒」。

10 月 9 日，微软发布 Microsoft-Decision-1。基座是 Qwen3.5-9B 后训练，Foundry 路径 `{foundry}/providers/microsoft/v1/systemone`，定价直接写成 0.042 美元/百万输入、输出免费。稿件举 Xbox Research 超过 1 万条反馈、Copilot 质检、值班检索。附录把 GPT-6 Luna Decisions 列为对比对象。

10 月 11 日前后，vLLM Semantic Router 开源 Decision 3.0。Hugging Face 上的 d3 能看多图和视频。模型卡 10 月 13 日在单卡 AMD MI325X 上测文本一问 p50 54.4 毫秒。智东西 10 月 12 日那篇「Jev 对手来了」，说的就是它。本百科已有单独的 Jev 横纵报告，这里只把它当作协议扩散的证据。

同一窗口里，阿里云百炼上线了决策模型 API。帮助中心页写：`POST /compatible-mode/v1/systemone`，模型 `decision-model-preview`，一次前向返回分类、评分、是非判断及概率，不生成文本。问题类型是 choice / noul / score，和 Jev 同构。Python 示例直接 `pip install typesafe-sdk`。官方返回示例带 `latency_ms: 52.9`。模型信息页更新时间 2026 年 10 月 11 日，北京和新加坡两地标「限时免费」，限流 1200 RPM、200 万 TPM，上下文 65536，最大输出长度 0。中国云厂商里，公开把 System One 做成一等 API 的，目前能核到的是阿里。

Anthropic 没有独立 Decisions。官方 ticket-routing 指南仍用 Messages + 小模型 + 强制 tool。Gemini 走 Interactions API 加 JSON Schema / `text/x.enum`。DeepSeek 补的是 Anthropic 兼容 `https://api.deepseek.com/anthropic`。月之暗面 Kimi 公开兼容列表有 chat completions、responses、messages，没有 `/v1/decisions`。百川开放平台未见 systemone。这些实验室选择继续用生成模型做判断，只是把 JSON 约束得更死。

### 1.5 混元停在会写 JSON 的快模型（到 2026 年 10 月 14 日）

hy 是混元在内部和 TokenHub 上的简称。TokenHub 模型 ID 已经从 `hunyuan-turbos-*`、`hunyuan-t1-*`、`hunyuan-functioncall` 迁到 `hy3` / `hy3-preview` / `hy4-preview`。旧版 ChatCompletions 的 `Tools` 曾绑定在 turbos、t1、functioncall 上。新文档把 Function Calling、`response_format.json_schema`、深度思考、Cache 写进 `hy3` 和 `hy4-preview`。

这些能力都还在写字。结构化输出保证字段形状，function call 保证工具参数 JSON，快思考（混元 Turbo S 那条「秒回」叙事，以及 TokenHub 的 `reasoning_effort`）缩短的是第一个生成 token。没有一条接口声明：我拒绝生成文本，只返回 predicate / choice / score。

TokenHub API 使用说明最近更新 2026-10-13 15:50:30。域名 `https://tokenhub.tencentmaas.com`，鉴权 Bearer，`GET /v1/models` 示例里是 `hy3` 和 `deepseek-v4-pro`。兼容协议是 OpenAI Chat Completions、OpenAI Responses、Anthropic Messages。`/v1/decisions` 和 `/v1/systemone` 在这一页上不存在。

混元原生 API 概览（1729/101848）列的是 ChatCompletions、ImageQuestion、GetEmbedding、生图、翻译。产品动态页检索「Decisions / System One / 决策模型」无官方宣布。公开 roadmap 暂缺。司内论坛那句「hy 什么时候可以出 Decisions API」，公网零命中，按司内讨论处理，不编造帖文和时间表。

腾讯云并不是没看见这个品类。CMR（Cloud Model Routing，产品 1829）2026 年 10 月 13 日 19:34:30 更新的《配置模型调度管理》写得很直白。步骤 1 选模态：文本生成、视频生成、向量嵌入、重排序、**分类决策模型（如 Jev 模型）**。步骤 3 意图路由有开关「开启分类决策模型」：开启后用本实例关联的分类决策模型做意图路由。客户端仍可走 OpenAI / Anthropic 兼容，Claude Code 文档把 `ANTHROPIC_MODEL=ModelRouter/auto` 指到 CMR。这是腾讯公有云上最接近 Decisions 的产品位。挂进去的决策模型，文档举例是 Jev，不是混元。

旁边还有两层更老的「意图」：云原生智能网关的意图识别路由，先调一个 NLU 再按置信度阈值（文档推荐 0.70）打到业务模型；智能体开发平台的「大模型意图识别节点」，画布里最多 20 个意图。前者多一次生成调用，后者是工作流节点。它们能分流，给不出 Luna / Jev 那种校准概率原语。

### 1.6 tt-switch：切的是谁来写字，不是谁来判断

公网没有腾讯官方把「tt-switch」登记成混元服务。能钉死的是同一形态的切换器。

CC Switch 是开源桌面应用，仓库 `farion1231/cc-switch`，MIT，Tauri 2。它给 Claude Code、Claude Desktop、Codex、Gemini CLI、Grok Build、OpenCode、OpenClaw、Hermes 做供应商一键切换，可选本机 sidecar（默认 `127.0.0.1:15721`）做协议转换。腾讯云 TokenHub 官方文档（1823/136605、1823/136601）教如何在 CC Switch 里接 Token Plan 企业版和个人版：Anthropic 走 `.../plan/anthropic`，OpenAI Completions 走 `.../plan/v3`。v3.19.1 给 Codex 加了「Tencent Hunyuan」预设，直连 `https://tokenhub.tencentmaas.com/v1`，`wire_api=responses`，模型 `hy3` / `hy3-preview`。GitHub issue #5592 要求加 Cursor 支持，被标重复后关闭，官方仍不支持 Cursor。

一份公开笔记把这套东西直接写成「TT switch」，标题是 OpenCode Zen 接入 Claude Code / TT switch，行为与 CC Switch 一致：本机代理、`PROXY_MANAGED`、模型映射，并写明其他 provider 包含「腾讯内网」。验证命令是 `curl http://127.0.0.1:<TT_SWITCH_PORT>/v1/messages?beta=true`。

据此可以下一个有证据的判断：腾讯员工口语里的 tt-switch / TT switch，很大概率就是 CC Switch 或内部 fork，用来把 Claude Code 在官方 Claude、腾讯内网、TokenHub 混元之间切换。它转换的是 Messages / Chat Completions / Responses。它不实现混元 Function Call，更没有 Decisions 协议。论坛说「让 tt-switch 接入下」，工程含义是：混元一旦有 `/v1/decisions` 或 `/v1/systemone`，在切换器里加一种协议、一个模型 ID，让内部工具沿用同一套 Key 和本地端口。司内若另有完全同名的网关服务，维护团队和内网 endpoint 公开材料暂缺，不编造。

若只看「接入速度」，OpenAI 自己的动作其实也分两截。Luna 作为生成模型是 9 月 22 日发布的；Decisions 专用通道晚了 14 天。SDK 在公开 beta 同一小时合进主干，说明接口形状事先锁死了，不是上线当天现写。阿里在 10 月 11 日的模型信息页上已经把最大输出长度写成 0，这是产品经理愿意承认「这个模型不会说话」的标志。混元到 10 月 14 日仍把 hy3 的卖点写在深度思考和 Function Calling 上。思考越深，离 Decisions 越远。决策模型要的是浅、快、校准、类型锁死。

纵向走到今天，故事卡在两截。外面：决策已经从「prompt 里求 JSON」变成独立端点，阿里比混元先把门开了。里面：tt-switch 很会给写字的模型换插头，判断这条线还插在生成模型的插座上。论坛把两截捏成一句话来问，听起来像一个功能请求，拆开是两个团队的活：模型侧要不要训头，网关侧要不要加协议。

---

## 二、横向分析：竞争图谱

> **切面时间**：2026 年 10 月 14 日。触发材料是司内论坛「hy 什么时候可以出 Decisions API，让 tt-switch 接入」。

### 2.1 竞品地图

这是场景 C。用户真正拿来对比的，不是「另一个聊天模型」，而是「谁能提供可嵌入控制流的判断」。选取六个代表：

1. **OpenAI Decisions API**：实验室给 Luna 开的专用通道，名字就是论坛在喊的那个词。
2. **Jev / System One**：品类定义者，MCP 和 hook 文档最全。
3. **阿里云 `decision-model-preview`**：中国云上已经能买到的 System One。
4. **Microsoft-Decision-1**：企业采购路径上的官方决策模型。
5. **混元 + TokenHub + CMR**：腾讯侧现状，槽位和模型错位。
6. **tt-switch / CC Switch**：本地接入层，决定内部工具明天能不能用上第 1 到第 5 项。

Cloudflare Clef 和 vLLM d3 在 Jev 专文里展开过，这里只在对照表里保留，避免把同一场四周竞赛写两遍。

### 2.2 Decisions API 当前画像

定位：应用服务器上的判断函数。官方 playground 让你先试 questions 和 input，再写代码。SDK 入口是 `client.decisions.create`。

一次典型调用像这样：工单文本进 `input`，`questions` 里并行放「是否报损」（predicate）、「派哪个组」（choice）、「紧急度」（score）。回来的 `answers` 按 `name` 对齐。choice 和 score 带 `probabilities` 与 `confidence`。应用自己设阈值：高置信度自动执行，低的转人工或升级到推理模型。

它明确不做什么。不写 tool arguments，不吐自定义 JSON 对象，不流式生成，beta 期间没有 prompt caching。图像必须 inline base64，不接受 URL 和 `file_id`。依赖前一答案的决策要拆成多次请求。

目标用户是要把判断写进代码的人：网关、客服路由、Agent 套件、语音动作选择。商业模式沿用 OpenAI 账号和 ZDR / HIPAA。口碑从社区帖就能读到两极：有人立刻拿去分类反馈；有人警告不要用 choice 做校准敏感的概率，predicate 更老实。

### 2.3 vs Jev：谁先定义协议，谁先长进套件

Jev 比 OpenAI Decisions 早 21 天进入 early access。开发者先记住的是 `state + questions` 和 noul/choice/score，不是 `input + predicate`。OpenAI 换了字段名，语义几乎一一对应：predicate ≈ noul。定价 Luna 约是 Jev 的 2.38 倍。Jev 官方延迟 70–500 毫秒，OpenAI 只给「约 10 倍于 Responses」。Jev 不能看图；Luna Decisions 能看 inline 图。Jev 权重封闭；OpenAI 走实验室账号。

调用形态上，Jev 更早长进 Agent 套件。官方 MCP 面向 Cursor；社区 `jev-use` 给 Claude Code 提供 `PreToolUse` 闸门：Bash / Write / Edit 在执行前先问 Jev 是否可逆，主模型零 token。jevwiki 把同一套 hook 映射到 Codex、Cursor `beforeShellExecution`、opencode。OpenAI 的官方套件路径是语音 Live + 服务端 Decisions，不是 Cursor 插件。

用户选 Jev，是因为文档、校准叙事、以及已经写好的 hook。用户选 OpenAI Decisions，是因为账号已经在、能看图、以后和 Responses / Agents 在同一栋楼。对腾讯内部，「合适的使用 API」这两家都能算合适，前提是数据能出境。出不了境，Jev 和 Luna 都过不了第一关。中文工单、中文代码评论、中文对话质检，Jev 文档自己写了 CJK 弱于英文、要自测。这是混元若出决策头，唯一不需要靠速度就能站住的理由：数据在境内，语言是主场。速度可以买开源 d3，语言和驻留买不来。

OpenAI 把 Decisions 做成 Luna 的专用通道，还有一层组织含义。Almeida 在 OpenAI 参与了让模型听话，离开后去做不说话的模型。老东家没有否认品类，而是把品类收进 GPT-6 的产品矩阵。混元没有这个传记包袱，也没有 Luna 那种现成小模型通道被写进模型卡。它要抄，抄的是接口和训练目标，抄不了「我们本来就有一条更快的 Luna」。因此「应该很容易」如果指 SDK 加一个 `client.decisions.create`，是的；如果指 hy3 明天改个路由就能当闸门，公开材料不支持这个乐观。

### 2.4 vs 阿里云决策模型：中国云已经开门

百炼的 `decision-model-preview` 走 TypeSafe System One，不是 OpenAI `/v1/decisions`。这对国内团队更省事：typesafe-sdk 换 `base_url` 就能打到北京或新加坡。工单分流示例一次请求问部门、是否升级、严重度，官方返回里 `latency_ms` 52.9、`confidence` 0.88 / 0.91。价格页写限时免费，不能当成长期单价。Function Calling、结构化输出、联网、微调，能力表上全是「不支持」——它承认自己不是生成模型。

和混元比，阿里把「决策」做成了独立模型 ID 和独立路径。混元把「判断」继续塞在 `hy3` 的 `json_schema` 里。论坛里那句「司内好像没有合适的使用 api」，对照百炼这一页，落差非常具体：阿里的开发者今天能 `POST .../systemone`；腾讯的开发者今天能 `POST .../chat/completions` 然后自己解析 JSON。解析这一步看起来小，落到 Agent 热路径上就是：多一次 schema 失败重试、多一段被模型写出来的解释、多一截无法设阈值的假置信度。百炼把最大输出长度写成 0，就是为了从根上取消这三笔开销。

阿里也没有宣布这套东西进了 CC Switch。Token Plan 文档有「接入决策模型」的评论审核教程，走的是 AI 工具扩展机制和 `/compatible-mode/v1/systemone`，仍然是应用侧调用。中国云赛道上，混元要追的第一名是这个端点，不是再发一个更快的 hy4。

### 2.5 vs 微软 Decision-1：采购路径，不是协议创新

Microsoft-Decision-1 抄的是 System One，价签对齐 Jev，基座是 9B 的 Qwen 后训练。它卖的是 Foundry 合规和「我们已经在 Xbox / Copilot 里用了」。对已经买 Azure 的企业，这降低安全审查摩擦。对腾讯，它提供一个参照：用现成的 Qwen 后训练，十天内可以做出可售的决策模型。混元自己有稠密和 MoE 权重，缺的不是基座，是把输出头从自回归生成改成并行打分，再配一套校准训练。微软稿件里的 35 倍、100 倍、200 倍都是对自家生成模型的相对值，不能直接拿来预测混元上线日。

后训练这条路值得单独说一句。Clef、Decision-1、d3 的骨干都是 Qwen 家族，冻结或轻量后训练，推理时对合法选项并行打分。混元若坚持「必须用自研基座才叫 hy Decisions」，日历会比「先用混元或通义做一版后训练头、挂上 CMR」更长。论坛要的是能用的 api，商标写在哪家权重上是第二问。TokenHub 已经在卖 DeepSeek、GLM、Kimi，决策头哪怕第一版不是混元自家名字，只要路径在、数据不出境，tt-switch 就可以接。坚持名字正确、接口缺席，是把品牌顺序放在了提效前面。

### 2.6 vs 混元栈：槽位在 CMR，模型在别处

把腾讯侧拆成三层，错位才会清楚。

**模型层（hy3 / hy4-preview）**：会聊天、会 tools、会 json_schema、会调 `reasoning_effort`。用它做意图判断，得到的是生成出来的标签。延迟跟生成走，校准没有官方成绩单。这是「可以凑合」，不是 Decisions。

**网关层（TokenHub）**：一 Key 调混元和第三方，协议停在写字。Cursor、CodeBuddy、Claude Code 的官方接入指南都指向这里。它今天切的是 `model` 字符串，不是 `questions` 数组。

**路由层（CMR）**：已经认识「分类决策模型」这个模态，举例 Jev，意图路由可开关。Claude Code 用 `ModelRouter/auto` 时，分流发生在网关，应用无感。这是腾讯云最接近「让 tt-switch 接入」的现成答案：tt-switch 把上游指到 CMR，CMR 挂 Jev 或未来的混元决策模型。混元自己不出模型，这个开关挂的就永远是别人的决策头。

智能体画布上的意图识别节点适合客服机器人，不适合 IDE 热路径。LLM-WAF 做的是放行/拦截/代答，是安全策略，不是给 Agent 当 Decisions 用的概率 API。

### 2.7 vs tt-switch：插头和插座

tt-switch 解决的问题是：Claude Code 今天打官方 Anthropic，明天打 TokenHub `hy3`，后天打腾讯内网，不要手改一堆环境变量。它是插头。Decisions 是一种新插座。

插头很好做。CC Switch 已经在 Completions、Responses、Anthropic Messages、Gemini Native 之间转换。再加 `/v1/decisions` 或 `/v1/systemone`，对切换器作者是增量协议。TokenHub 官方既然已经为 CC Switch 写了两页文档，混元 Decisions 一旦存在，最省事的分发就是：TokenHub 暴露端点，CC Switch / tt-switch 加预设，内部论坛那句话就算落地。

插头解决不了插座空着。Cursor 还不受 CC Switch 支持，内部若主力是 Cursor，tt-switch 接入也喂不到对话里。那条路径要手改 Cursor 的 OpenAI 兼容 Base URL，或自建 MCP 把 Decisions 包成 tool。后者能用，会把判断重新塞回「模型决定调不调工具」的慢循环。

### 2.8 这种 API 究竟怎么被调用

用户问：是接入工作流，还是像 Cursor 这样的 IDE 会通过 MCP 嵌在对话里触发？答案是四条路同时存在，快慢差一个数量级。主路不是 MCP。

**第一条，应用侧路。这是 OpenAI 官方设计。** 工单系统、网关、语音后端在服务端 `POST /v1/decisions`，密钥不进浏览器、不进 IDE。返回值进业务 `if`：派哪个队列、是否退款、要不要升级模型。Vercel AI Gateway 已经暴露兼容的 `/v1/decisions`，模型 ID 写成 `openai/gpt-6-luna-decisions`，AI SDK 有 `experimental_decide`。LangChain 一类编排器把决策节点画在图里，和「工作流」是同一件事。

**第二条，Agent 套件钩子，对话外拦截。** Claude Code `PreToolUse`、Cursor `beforeShellExecution`、Codex 同名 hook，在工具真正执行前问决策模型：这次 `rm` 可不可逆、这次 `git push` 要不要人看。`jev-use hook gate` 写明：主模型零 token，Jev 不可达则 fail open。这是 IDE 里最值钱的用法，而且用户看不见一次「工具调用」气泡。判断发生在套件层，不发生在对话层。

**第三条，MCP 工具，对话内触发。** Cursor 读 `.cursor/mcp.json`，Jev 的 MCP 提供 `jev_classify` / `jev_score` / `jev_check` / `jev_gate` / `jev_decide`。Agent 在任务中途「想起来」可以问一句。代价是：主模型必须先决定调用这个 tool，判断的延迟叠在一轮 function calling 上。MCP 文档自己也写：Jev 看不见对话和本地文件，state 要调用方喂全。把 Decisions 理解成「Cursor 里自动冒出来的意图判断」，和现有实现不符。OpenAI 没有官方 Decisions MCP。

**第四条，网关意图路由，调用方无感。** CMR `ModelRouter/auto`、云原生网关的 NLU 分流、Semantic Router 论文里的「何时推理」，请求进门时已经被打到便宜或昂贵的后端。应用仍发聊天协议。这是 tt-switch 最容易接的形态：切换器只换 Base URL，决策发生在上游。

语音是第一条的变体。GPT-Live 不停，Decisions 在旁边选动作。幻灯片「下一页」走 choice，`reason` 再转推理模型。Cursor 聊天没有对等的 delegation 窗口。

把四条路放进一条内部编码任务里，快慢差会变得非常具体。假设用户在 Claude Code 里说「把这次的错误日志归到哪个组和要不要热修」。主模型若自己用 tools 分类，至少要生成一串 JSON，再被解析，再决定下一步，前后一两秒很常见。若 PreToolUse 或服务端先打 Decisions：choice 选出 `platform` / `backend` / `client`，predicate 给出「是否热修」的概率，50 到 200 毫秒后规则引擎已经分支。主模型接到的是已经切好的上下文，只负责改代码。MCP 路径夹在中间：主模型先「想到」要调 `jev_decide`，写一次 tool call，等 MCP 返回，再继续。能用，比全程生成稳，比 hook 慢，而且模型可能根本想不起来调。

Cursor 对话里的情形更苛刻。Agent 已经带着一长串 MCP。每多一个 tool，选错工具的概率上升。把 Decisions 做成其中之一，等于用贵模型去决定要不要用便宜模型。官方设计把这个决定从模型手里拿走：应用或套件在模型开口之前就问完。这是「嵌在对话中被触发」听起来方便、做起来亏的原因。

所以：工作流 / 网关 / 套件 hook 是 Decisions 的主场；MCP 是可选的慢封装；把希望寄托在「对话模型自己触发」上，会把这个品类做回去。内部若只让 tt-switch 把混元 Decisions 暴露成又一个 chat model，开发者仍会用 prompt 求 JSON，论坛想要的提效不会出现。

### 2.9 维度对照

| 维度 | OpenAI Decisions | Jev | 阿里 decision-model-preview | 微软 Decision-1 | 混元现状 | tt-switch |
|------|------------------|-----|------------------------------|-----------------|----------|-----------|
| 公开时间 | 2026-10-06 beta | 2026-09-15 | 文档见 2026-10-11 | 2026-10-09 | 无独立端点 | 社区工具；TokenHub 文档已教接入 |
| 路径 | `POST /v1/decisions` | `/v1/systemone` 或 `/v1/decide` | `/compatible-mode/v1/systemone` | Foundry `/v1/systemone` | Chat Completions / Responses / Messages | 本地转换上述写字协议 |
| 模型 | `gpt-6-luna` | `jev-latest` 等 | `decision-model-preview` | Microsoft-Decision-1 | `hy3` / `hy4-preview` | 不生产模型 |
| 原语 | predicate / choice / score | noul / choice / score | 同 Jev | 同 Jev | JSON / tool calls | 无 |
| 输入价 | 0.10 美元/百万 token | 0.042 美元/百万 | 限时免费（长期价暂缺） | 0.042 美元/百万 | 按生成模型计 | 本机免费 |
| 官方延迟 | 约 10× Responses；无 ms | 70–500 ms | 示例 52.9 ms | 相对 GPT-6 Sol ~35× | 生成时延 | 本机代理开销 |
| 图像 | inline 图 | 无 | 文本 | 文本为主 | 视具体 hy 模型 | 透传 |
| IDE 主路径 | 服务端；语音 delegation | MCP + PreToolUse hook | 应用扩展 / API | Foundry | 无 | 切 Claude Code / Codex 供应商 |
| 国内合规 | 美欧 residency | 美西节点 | 北京 / 新加坡 | Azure | 国内 TokenHub | 可指内网 |

### 2.10 生态位与格局

品类已经从「Jev 一家定义」变成「协议竞赛」。接口几乎同构，差异在延迟、校准、能否看图、数据驻留。格局是百花齐放，没有两强争霸。混元缺席的是模型，不是认知：CMR 文档把 Jev 写进模态列表，说明腾讯云产品侧已经把分类决策当成一等公民。tt-switch 站在客户端，生态位是「让内部 IDE 换上游」，它填补的空白是配置，不是智能。

用户真实选择很分层。能出海的团队，OpenAI Decisions 和 Jev 今天就能嵌进工作流。必须留在国内的团队，阿里 systemone 是现成插座，腾讯 CMR+Jev 是网关插座，混元自己是空的。写 Claude Code 的人会催 tt-switch；写 Cursor 的人催了也暂时接不上，要另开 MCP 或手改 Base URL。CodeBuddy 走 TokenHub 官方接入，和 Cursor 一样吃的是写字协议，短时间内不会因为 tt-switch 多一个预设就自动出现意图闸门。谁在哪一种 IDE 里编码，决定了「接入」三个字落在 hook、MCP 还是网关。论坛把它们写成同一个需求，落地时会拆成三条补丁。

---

## 三、横纵交汇洞察

### 3.1 历史如何塑造了当下位置

Function calling 把判断塞进会写字的模型，锁死了 2023 到 2025 年所有「智能路由」的样子：先生成，再解析，再重试。Jev 把生成拿掉，协议才能薄到可以当函数。OpenAI 用 Luna 另开端点，承认品类，但继承了「大模型做判断」的实验室路径，所以贵一点、官方延迟叙事也只敢写相对 Responses 的 10 倍。阿里直接兼容 System One，用 typesafe-sdk，等于承认协议标准已经不在自己手里。

混元的历史选择是另一条：把 functioncall、turbos、t1 收进 `hy3`，把思考开关收成 `reasoning_effort`，把网关做成 TokenHub 三协议。这些选择让混元在 Coding Agent 里很好用，也让它错过「输出长度为零」这一跳。CMR 愿意挂 Jev，说明产品经理看见了缺口；模型侧还在优化写代码。缺口于是表现为论坛提问。

tt-switch 的历史更短，路径更窄。它跟着 Claude Code 的 Anthropic 协议长出来，官方被 TokenHub 收编进接入文档。它从来只转换「谁来生成下一串 token」。要它接入 Decisions，必须先有一种不是 chat 的上游。历史把它放在插头的位置上，插座却还没打孔。

### 3.2 优势与劣势的历史根源

**强项：判断从 prompt 里搬进了类型。** 根源是 Almeida 拒绝再让模型对人说话。没有 9 月 15 日那一刀，10 月不会有五家抄同一张表。

**强项：调用可以完全离开对话。** 根源是 OpenAI 把密钥留服务端、Jev 把 gate 做成 hook。套件作者发现，最值钱的判断发生在工具执行前，不发生在聊天气泡里。

**强项：腾讯云网关已经认识这个模态。** 根源是 CMR 要把意图路由做成可卖的企业功能，Jev 是最快能填进去的外脑。

**包袱：混元的产品惯性是生成。** `hy3` 越会写代码、越会 tools，内部就越容易觉得「json_schema 已经够用」。够用生成标签，不够用当 50 毫秒的闸门。

**包袱：tt-switch 覆盖不到 Cursor。** 根源是 CC Switch 的工具名单里从来没有 Cursor。论坛如果混用「所有内部 IDE」，接入日会对不上。Cursor 吃 OpenAI 兼容协议，TokenHub 已经有 `/v1` 和 `/v1/chat/completions`；缺的仍是 Decisions 那条路径。即便混元明天开孔，Cursor 也要在模型设置里加一个自定义端点，或等某个内部 MCP 把 `hy-decisions` 包成 tool。切换器解决不了 IDE 厂商自己的协议清单。

**包袱：choice 的校准陷阱。** OpenAI 社区用硬币实验打过脸。混元若上线日只抄 choice、不提供可靠的 predicate/noul，工具链会把错误的高置信度写进自动执行。predicate 问的是「这件事是不是真的」，概率轴是连续的；choice 问的是「在这几个名字里选一个」，模型容易把质量压到看起来最像的那一项上。工单分流用 choice 没问题，安全闸门应当用 predicate。接口抄齐三种原语，不等于三种都能拿来设阈值。

当初把 Function Calling 做进混元，是正确的 2024 年决策。2026 年 10 月，它变成一种错觉：有 tools 就等于有 Decisions。tools 是模型请求执行并填写参数；Decisions 是应用先判定再执行，模型不写参数。两件事在官方文档里被 OpenAI 写成并列的「不要混用」。

### 3.3 未来三个剧本

- **最可能**：混元短期内不出对等的自研决策模型。内部要提效，走 CMR 挂 Jev 或直连百炼 / OpenAI Decisions；TokenHub 继续只做写字协议。tt-switch 加一个「决策上游」预设，指到 CMR 或外部 systemone，而不是等 `hy-decisions` 这个模型 ID。论坛提问会再出现几次，答案是「先用网关槽」。时间尺度：数周到一个季度能看到网关侧的说明，混元模型卡上出现独立决策 ID 的公开计划仍暂缺。`hy3` json_schema 会继续被当成权宜之计，延迟和校准都不会让人满意。

- **最危险**：混元用 `hy4-preview` 套一层 schema，对外叫 Decisions，tt-switch 也接了。调用方以为拿到了 50 毫秒的闸门，实际仍在付生成时延，choice 置信度不可设阈值。IDE 热路径上的误拦截和漏拦截一起出现：该拦的 `rm` 没拦，不该拦的 `ls` 被 hook 挡住。品类在司内被写坏，再要推真正的并行打分模型，会先撞上一次「我们试过，不好用」。

- **最乐观**：混元用现有权重做后训练，CMR 文档里的「分类决策模型」换上自研 ID，TokenHub 增加 `/v1/decisions` 或 `/v1/systemone`，tt-switch 加协议，Claude Code 的 PreToolUse 和内部工作流共用一个国内端点。阿里已经证明接口可以在 OpenAI 公测后数日内出现；微软证明 9B 后训练可以上架。混元有数据驻留优势，中文工单和中文代码 diff 是 Jev 文档自己划的弱区。这条剧本需要的不是再发一篇「混元更会思考」，而是年报式的产品页：最大输出长度 0、原语三选一、给出可复核的延迟和 ECE。

我的判断靠近「最可能」偏积极的一侧。积极在网关：CMR 已经把开关做出来，tt-switch 接 CMR 比等混元训头更快。保守在模型：公开材料里看不到混元决策头的训练叙事，不能把阿里的速度外推成混元的承诺。10 月 13 日 TokenHub 和 CMR 两页文档同一天更新，一边仍无 Decisions 路径，一边已能挂 Jev。产品侧的优先级，写在这两页的差异里。

对「应该很容易吧」这个问题，可以分三层答。协议翻译很容易，CC Switch 一直在做这种活。网关挂 Jev 也很容易，文档开关已经在。自研一个让人敢把阈值写进生产的混元 Decisions，取决于校准数据、中文评测和是否肯把输出长度做成零。后一件事，OpenAI 用现成 Luna 开通道都还只敢标 beta；混元没有 Luna 那种现成的「决策专用推理路径」被写进模型卡。容易的是接入，不容易的是判断本身变得可依赖。

若一定要给内部排期一个可操作的顺序，我愿意把「容易」写成三张工单，而不是一个上线日。工单 A：CMR 实例关联 Jev 或百炼 systemone，意图路由打开「分类决策模型」，tt-switch 增加一个 CMR 上游。这一张不碰混元权重，公开文档已经够写 runbook。工单 B：TokenHub 增加 `/v1/decisions` 或 `/v1/systemone` 的协议兼容，先把外部决策模型纳管进来，模型 ID 可以暂时不是 `hy-*`。工单 C：混元训决策头，最大输出长度写成 0，给出中文工单和代码 diff 上的延迟与校准。论坛问的是 C，开发者下周能用的是 A。把 C 的等待投射到 A 上，才会觉得「怎么还不让 tt-switch 接入」。tt-switch 能接的，今天就是 A 和 B。

调用方式上，内部该怎么接，也可以说具体。工作流、客服、内容审核：服务端直打 Decisions / systemone，结果进规则引擎，不要进聊天记录。Claude Code / Codex：hook 闸门走决策模型，主模型继续写代码；tt-switch 只负责把 hook 的上游指到国内端点。Cursor：今天用 Jev MCP 或自建 MCP 包一层；不要等 tt-switch。CMR：把 ModelRouter 打开，分类决策挂 Jev 或未来的 hy 决策模型，应用继续发 Messages。四条路里，MCP 嵌在对话中是补充，不是主路径。论坛想要的「简单快速的意图判断」，发生在对话开始之前，以及工具执行之前。

还有一种会被低估的接法：批量。客服夜里积压一万条评论，决策模型按条打 choice，置信度低于阈值的才进人工队列。Jev 和百炼的文档都把这一类写成主场景。它和 IDE 无关，和 tt-switch 也无关，却是「合适的使用 api」四个字里人数最多的那群人。如果混元只为 Coding Agent 做 Decisions，会把这条现金流和这条稳定性验证一起丢掉。校准必须在批量数据上度量，IDE 热路径的样本太少，不够把 ECE 跑出来。先服务工单，再服务 hook，顺序反过来，阈值会拍脑袋。

把时间再拉长一格。2022 年的 Moderation 是固定类别的审核函数。2023 年的 Function calling 是模型请求工具。2024 年的 Structured Outputs 是生成被 schema 锁住。2026 年 9 月的 Jev 是生成被取消。2026 年 10 月的 Decisions API 是实验室承认：软件要的判断，不应该再从一段散文里挖。混元还站在 2024 年那一格，只是模型更强、网关更全。tt-switch 站在客户端，等的是 2026 年那一格的插座。插座一旦打孔，接入不会难。打孔之前，催 tt-switch 解决不了论坛里的那句话。

我愿意把这句话翻译成内部能分发的口径。Decisions API 是给软件用的判断函数，不是给聊天用的新模型。tt-switch 是给 IDE 换上游的插头，公网对应 CC Switch 一类切换器，不是混元本体。调用主场在工作流、网关和工具钩子，MCP 只是对话里的慢封装。混元公开侧还没有这个函数；腾讯云 CMR 已经为 Jev 留了槽。想提效的人，先把槽用上。想等 hy 两个字母印在模型 ID 上的人，公开材料给不出日期。容易的是插头，缺的是插座。口径只此一段，后面都是证据。若有人追问「那我们自己用 hy3 先顶上行不行」，行，当作过渡，不要写进闸门的自动执行。json_schema 可以分流，不宜拿生成出来的「把握」去拦 `rm`。过渡期的正确姿势是：分类可以自动，破坏性动作仍然问人。等真正的决策端点给出可复核的概率，再把阈值往下拧。过渡期多花一点人工确认，比把未校准的 JSON 写进生产更便宜。闸门一旦误伤开发者日常命令，决策 API 会在内部先失去信任，再失去预算。信任要用批量评测换，不能用上线日换。评测集先放中文工单和代码 diff，再放英文公开题，顺序反了会重复 Jev 在 CJK 上已经写下的弱点。

---

## 四、信息来源

1. [OpenAI Decisions 指南](https://developers.openai.com/api/docs/guides/decisions) — 访问日期 2026-10-14 — 端点、三类型、定价 0.10 美元/百万输入、约 10× Responses、SDK 版本、GA 预期
2. [Connect voice to Decisions](https://developers.openai.com/api/docs/guides/decisions-voice) — 访问日期 2026-10-14 — client-delegation、choice 选动作、reason 转 Responses
3. [OpenAI 开发者社区：Decisions API Public Beta](https://community.openai.com/t/decisions-api-is-now-available-in-public-beta/1403877) — 访问日期 2026-10-14 — 2026-10-06 20:53 UTC、社区延迟与校准讨论
4. [openai-python PR #4033](https://github.com/openai/openai-python/pull/4033) — 访问日期 2026-10-14 — 2026-10-06 合并，`decisions.create`
5. [TypeSafe：Introducing System One Models & Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev) — 访问日期 2026-10-14 — 2026-09-15、RLCD、0.042 美元/百万 token
6. [阿里云：决策模型 System One API](https://help.aliyun.com/zh/model-studio/decision-model-api) — 访问日期 2026-10-14 — `decision-model-preview`、`/v1/systemone`、示例 latency_ms 52.9
7. [阿里云：decision-model-preview 模型信息](https://www.alibabacloud.com/help/zh/model-studio/decision-model-preview) — 访问日期 2026-10-14 — 更新 2026-10-11、输出长度 0、限时免费
8. [腾讯云 CMR：配置模型调度管理](https://cloud.tencent.com/document/product/1829/134681) — 访问日期 2026-10-14 — 更新 2026-10-13、分类决策模型如 Jev、开启分类决策模型
9. [腾讯云 TokenHub API 使用说明](https://cloud.tencent.com/document/product/1823/130078) — 访问日期 2026-10-14 — 更新 2026-10-13、无 `/v1/decisions`、模型表示例 hy3
10. [腾讯云 TokenHub × CC Switch 企业版](https://cloud.tencent.com/document/product/1823/136605) — 访问日期 2026-10-14 — 官方教 CC Switch 接 Token Plan
11. [CC Switch v3.19.1](https://github.com/farion1231/cc-switch/releases/tag/v3.19.1) — 访问日期 2026-10-14 — Codex 腾讯混元预设、Cursor 不在支持列表
12. [TT switch 公开笔记](https://github.com/challenwang408408/share-storage-project/blob/main/opencode-zen-claude-code-compat.md) — 访问日期 2026-10-14 — TT switch、腾讯内网、本地 `/v1/messages`
13. [Jev × Cursor MCP](https://www.jevtypesafeai.com/integrations/cursor) — 访问日期 2026-10-14 — `jev_decide` 等工具、`.cursor/mcp.json`
14. [jevwiki：Jev in agent harnesses](https://jevwiki.ai/wiki/guides/jev-in-agent-harnesses.md) — 访问日期 2026-10-14 — PreToolUse / beforeShellExecution
15. [Microsoft-Decision-1](https://commandline.microsoft.com/microsoft-decision-1-model-foundry/) — 访问日期 2026-10-14 — 2026-10-09、0.042 美元/百万输入
16. [Cloudflare Clef](https://blog.cloudflare.com/clef-decision-models/) — 访问日期 2026-10-14 — 2026-10-01、System One 兼容
17. [arxiv 2510.08731](https://arxiv.org/abs/2510.08731) — 访问日期 2026-10-14 — Semantic Router 论文
18. [Vercel：OpenAI-Compatible Decisions](https://vercel.com/docs/ai-gateway/sdks-and-apis/openai-decisions) — 访问日期 2026-10-14 — 网关 `/v1/decisions`
19. [OpenAI DevDay 2026 Recap](https://openai.com/index/devday-2026-recap/) — 访问日期 2026-10-14 — 2026-09-29 limited preview
20. [混元 ChatCompletions / Tools](https://cloud.tencent.com/document/product/1729/105701) — 访问日期 2026-10-14 — functioncall 仍为生成路径

## 五、方法论说明

本文采用横纵分析法（Horizontal-Vertical Analysis）。纵轴沿时间还原决策模型从分类器、Function calling 到独立 Decisions 端点的历程，横轴对比 OpenAI、Jev、阿里、微软、混元栈与 tt-switch，交汇后回答「hy 何时能出、该怎么接、调用发生在哪一层」。方法论由数字生命卡兹克提出；本报告由玉笛百科撰写。

司内论坛原帖、tt-switch 内部仓库与维护团队、混元 Decisions roadmap，公开检索均为暂缺，不编造。滚动延迟与校准数字以各厂商文档和社区实验为准，已标明性质。本报告不构成采购或接入承诺。
