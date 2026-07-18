# Test6 — 用 OpenCode 交付 MiniClaw WeLink 助理

本目录演示在 **OpenCode** 中用两种方式生成 `welinkcli_agent.py`：

- **方案 A（规范流水线）**：OpenSpec 管规格 + Superpowers 管开发 + Code Review 兜底，可追溯、可复用。
- **方案 B（Vibe Coding 简化版）**：直接把现成的 `SPEC.md` 喂给 OpenCode，一次生成，快速验证。

```
方案 A：想法/需求 ──OpenSpec──▶ SPEC.md ──Superpowers──▶ 实现 ──Code Review──▶ 交付物
方案 B：           SPEC.md（已有）────────直接 prompt──────────▶ 实现 ──迭代修复──▶ 交付物
```

> `welinkcli_agent.py` 是按方案 A 产出的**参考实现**，[`SPEC.md`](SPEC.md) 是它的实现契约。方案 B 正是利用这份契约"复现"实现。

---

## 0. 环境准备

### 0.1 `.opencode/` 目录说明（已按 OpenCode 约定预装）

本目录的 `.opencode/` 已按 OpenCode 官方约定预装好，结构是正确的：

```
.opencode/
├── commands/          # 自定义斜杠命令（OpenCode 项目级目录，复数 commands/）
│   ├── opsx-propose.md    → /opsx-propose
│   ├── opsx-apply.md      → /opsx-apply
│   ├── opsx-explore.md    → /opsx-explore
│   ├── opsx-archive.md    → /opsx-archive
│   └── opsx-sync.md       → /opsx-sync
└── skills/            # Agent 技能（.opencode/skills/<name>/SKILL.md）
    ├── openspec-*         # OpenSpec 五个技能
    ├── brainstorming / writing-plans / executing-plans / ...   # Superpowers
    └── code-review-skill / requesting-code-review / ...        # Code Review
```

要点：

- `commands/`（复数）是 OpenCode 的项目级命令目录，文件名即命令名（`opsx-propose.md` → `/opsx-propose`）。这与 Claude Code 的 `.claude/commands/` 不同，不要混用。
- `skills/<name>/SKILL.md` 是 OpenCode 原生技能格式，frontmatter 的 `name` 必须与目录名一致（本目录已全部校验通过）。
- 不需要 `opencode.json` 或 `AGENTS.md` 也能工作；它们只在你需要改配置/加全局约定时才加。
- **发现机制**：OpenCode 从当前工作目录向上走到 git 根，加载沿途的 `.opencode/commands/` 和 `.opencode/skills/`。所以**必须在 `test6/` 目录（或其子目录）里启动 `opencode`**；在仓库根目录启动则加载不到本目录的命令和技能。

### 0.2 安装依赖

```bash
# 1) OpenCode（任选其一）
npm i -g opencode-ai@latest          # 或 brew install opencode-ai/tap/opencode

# 2) OpenSpec CLI（方案 A 需要；opsx 命令底层调它，需 Node.js ≥ 20.19）
npm install -g @fission-ai/openspec@latest

# 3) 在 test6 下初始化 OpenSpec（生成 openspec/ 目录，opsx 命令的工作根）
cd test6
openspec init --tools opencode       # .opencode/ 已预装，init 会检测并保留
```

### 0.3 启动

```bash
cd test6        # 关键：在 test6 里启动，才能加载 .opencode/ 下的命令和技能
opencode
```

---

## 方案 A：OpenSpec + Superpowers 流水线

三个阶段各司其职：

| 阶段 | 工具 | 输入 | 输出 | 解决的问题 |
|------|------|------|------|-----------|
| ① 规格 | **OpenSpec**（`/opsx-*` 命令 + `openspec-*` 技能） | 自然语言需求 | `openspec/changes/*` → `SPEC.md` | 把"要做什么"变成"怎么做"的契约 |
| ② 开发 | **Superpowers**（`brainstorming` 等技能） | 规格/设计 | 实现代码 | 先想清楚再写，避免返工 |
| ③ 审查 | **Code Review**（`requesting-code-review` / `code-review-skill`） | 实现代码 | 缺陷清单 + 修复 | 上线前兜底，抓 bug 与坏味道 |

### ① 用 OpenSpec 把需求变成规格

直接让 AI 写代码，它只会写"大概对"的代码。先把需求固化为**实现契约**，后续每一步都有据可依。

在 OpenCode 中依次执行：

```
/opsx-explore          # （可选）无压力地想清楚：探索方案、权衡取舍

/opsx-propose 开发一个 WeLink 群聊 AI 助理（welinkcli_agent.py，单文件）：
- 通过 welink-cli（子进程）轮询群消息、发送回复
- 用 CrewAI Agent 生成回复，复用根目录 llm/llm.py 的 LoggedLLM
- 支持多模态（图片理解）和技能扩展（会议纪要、图片分析）
- 消息去重（持久化），不重复回复、不回复自身
- 配置走根目录 .env
```

`/opsx-propose` 会在 `openspec/changes/<name>/` 下生成提案三件套：`proposal.md`（做什么/为什么）、`design.md`（怎么做）、`tasks.md`（实现步骤）。确认后继续：

```
/opsx-apply            # 按 tasks.md 实现该 change
/opsx-archive          # 完成后归档，规格沉淀到 openspec/specs/
```

本目录的 [`SPEC.md`](SPEC.md) 就是这一阶段沉淀出的实现契约，至少要写清：

1. **外部接口契约**：welink-cli 的命令格式与返回 JSON 结构（`respData.chatInfo`、`msgId`、`serverSendTime`…）
2. **模块实现契约**：每个类/函数的签名、参数、返回值、异常处理
3. **关键规则**：去重逻辑、主循环过滤（过短/自身消息要先 `mark_replied` 再跳过）、排序（按时间降序）
4. **验收标准**：可逐条勾选的测试场景

### ② 用 Superpowers 头脑风暴 + 开发

**先 brainstorming，再动手。** `brainstorming` 技能的硬性要求：任何创造性工作开始前，先讨论清楚再实现。在编码前让 OpenCode 加载它：

```
使用 brainstorming 技能，基于 SPEC.md 帮我讨论几个设计决策：
1. 单文件 vs 多文件：教学项目倾向单文件，用注释分块
2. 去重：持久化 JSON（支持重启恢复）vs 内存 set
3. 图片处理：先下载到本地再 base64，还是内存中转
4. 技能扩展：SKILL.md 文件加载 + 动态 Sub-Crew
```

设计定稿后，用开发类技能（`writing-plans` / `executing-plans` / `subagent-driven-development`）按 SPEC 的模块布局逐步实现：

```
请按 SPEC.md 的"单文件模块布局"顺序实现 welinkcli_agent.py：
配置 → InboundMessage → 导入 LoggedLLM → AddImageTool →
load_skills/SKILLS → SkillLoaderTool → create_main_agent → WeLink CLI 函数 →
RepliedTracker → handle_message/build_prompt → main()
```

要点（SPEC 已写死，实现时严格遵守）：

- LLM 用 `from llm.llm import LoggedLLM`，构造时**显式传 `model`**。
- 技能从 `skills/<name>/SKILL.md` 文件加载（`load_skills()` 解析 frontmatter + 正文），`SkillLoaderTool` 复用根目录 `tools/skill_loader_tool.py`。
- 主循环过滤时，过短/自身消息要先 `mark_replied` 再 `continue`，否则队列卡死。

### ③ 用 Code Review 审查并修复

实现完成后、交付前过一遍审查。让 OpenCode 加载 `requesting-code-review` 技能审查 `welinkcli_agent.py`，审查维度参考：

| 维度 | 本项目重点 |
|------|-----------|
| 正确性 | subprocess 超时、JSON 解析异常、`respData` 为 null、去重逻辑 |
| 健壮性 | 网络超时、文件 IO、LLM 失败不中断主循环 |
| 安全 | API Key 走环境变量不硬编码 |
| 可维护性 | 类型注解、docstring、模块边界 |

把缺陷交回开发技能修复，用 `verification-before-completion` / `systematic-debugging` 验证，最后 `receiving-code-review` 复核。

> 本项目的 `welinkcli_agent.py` 已经过一轮 Code Review：修复了消息队列卡死、未排序、`respData` 为 null 崩溃、配置非整数启动崩溃等缺陷。

---

## 方案 B：Vibe Coding —— 直接用 SPEC.md 生成

如果规格已经写好了（比如本目录现成的 `SPEC.md`），可以跳过整个 OpenSpec 流程，让 OpenCode 直接照着契约写代码。这是"规格驱动"的最轻形态：**SPEC 即 prompt**。

### 怎么做

```bash
cd test6 && opencode
```

然后直接给指令（`@` 可以把文件注入上下文）：

```
阅读 @SPEC.md，严格按照其中的实现契约生成 welinkcli_agent.py：
- 模块布局、函数签名、异常处理、关键规则都以 SPEC.md 为准
- 技能按 5.5 节从 skills/<name>/SKILL.md 加载，复用 tools/skill_loader_tool.py
- 生成后运行 python -m py_compile welinkcli_agent.py 自检
```

可选的稳妥做法：先按 `Tab` 切到 **plan agent**（只读，不会改文件），让它根据 SPEC.md 输出实现计划，你确认后再切回 **build agent** 执行。

### 迭代修复

生成后跑一遍，把报错原样贴回去即可：

```
运行 python test6/welinkcli_agent.py 报错：<粘贴报错>，请修复
```

### 方案 A vs 方案 B

| | 方案 A：OpenSpec + Superpowers | 方案 B：直接用 SPEC.md |
|---|---|---|
| 适用场景 | 需求还在演进、团队协作、需要决策留痕 | 规格已确定、快速复现/原型、一次性脚本 |
| 规格来源 | `/opsx-propose` 现场生成并维护在 `openspec/` | 现成的 SPEC.md（方案 A 的沉淀产物） |
| 可追溯性 | 高（proposal/design/tasks 全程留档） | 低（只有 SPEC 和最终代码） |
| 成本 | 多轮交互，慢但稳 | 一条 prompt，快但依赖 SPEC 质量 |
| 关系 | 生产 SPEC | 消费 SPEC |

两者不是二选一：常见用法是**第一次用方案 A 产出 SPEC.md，之后重建/移植/教学演示时用方案 B 快速复现**。方案 B 的生成质量上限就是 SPEC.md 的详细程度——契约越精确，一次通过率越高。

---

## 快速开始（运行参考实现）

```bash
# 1. 依赖
pip install -r requirements.txt      # 建议在根目录 .venv 中执行

# 2. 配置根目录 .env（OPENAI_*、WELINK_GROUP_ID 等）

# 3. 确保 welink-cli 可用并已登录
welink-cli --version

# 4. 运行
python test6/welinkcli_agent.py
```

在 WeLink 群里测试：发文本"帮我整理会议纪要"；发截图 + "看看这个报错"。

---

## 运行流程图（welinkcli_agent.py 运行时）

```
                  启动 welinkcli_agent.py
                          │
                          ▼
   ┌───────────────────────────────────────────────┐
   │ main() 启动初始化                              │
   │  ① 校验 WELINK_GROUP_ID / OPENAI_API_KEY      │
   │  ② ensure_workspace（创建 workspace/{群id}）   │
   │  ③ 创建 LoggedLLM + 主 Agent                  │
   │     工具：FileWriter/FileRead/AddImage/         │
   │           SkillLoaderTool，开启 multimodal     │
   │  ④ RepliedTracker（从 JSON 加载已回复记录）     │
   └────────────────────┬──────────────────────────┘
                        ▼
          ┌──────────────────────────┐
          │    while True 主循环      │◀─────────────────┐
          └────────────┬─────────────┘                   │
                       ▼                                  │
        ┌───────────────────────────────┐                │
        │ get_recent_messages()         │                │
        │  welink-cli 拉取群最近消息     │                │
        │  → 解析 respData.chatInfo      │                │
        │  → 按时间降序排序              │                │
        └───────────────┬───────────────┘                │
                        ▼                                │
                 无消息？ ──是──▶ sleep ──────────────────┤
                        │否                               │
                        ▼                                │
                 latest = messages[0]                    │
                        ▼                                │
                 已回复过？ ──是──▶ sleep ────────────────┤
                        │否                               │
                        ▼                                │
        ┌───────────────────────────────┐                │
        │ 文本过短 / 是自身消息？        │                │
        │   是 → mark_replied → 跳过     │────────────────┤
        └───────────────┬───────────────┘                │
                        ▼否                              │
        ┌───────────────────────────────┐                │
        │ build_prompt()                │                │
        │  有图片 → 下载到本地           │                │
        │  无图片 → 直接用文本           │                │
        └───────────────┬───────────────┘                │
                        ▼                                │
        ┌───────────────────────────────┐                │
        │ handle_message()              │                │
        │  agent.kickoff(prompt)        │                │
        │  Agent 推理：选工具/技能生成回复│                │
        │  （可能调用 add_image /        │                │
        │   skill_loader 等工具）        │                │
        └───────────────┬───────────────┘                │
                        ▼                                │
                 有回复？ ──否────────────────────────────┤
                        │是                              │
                        ▼                                │
        ┌───────────────────────────────┐                │
        │ send_to_group()               │                │
        │  welink-cli 发送【AI助手】回复 │                │
        │  → mark_replied(msg_id)       │                │
        └───────────────┬───────────────┘                │
                        ▼                                │
              sleep(CHECK_INTERVAL) ─────────────────────┘
```

> 核心是一个轮询循环：拉消息 → 去重/过滤（已回复、过短、自身消息都要先 `mark_replied` 再跳过）→ Agent 生成回复 → 回群。`RepliedTracker` 持久化到 JSON，重启后不重复回复。

---

## 文件说明

| 文件/目录 | 角色 |
|------|------|
| `SPEC.md` | 实现契约（方案 A 产物，方案 B 的输入） |
| `welinkcli_agent.py` | 参考实现（CrewAI Agent 版） |
| `welinkcli_llm.py` | 直接 LLM 调用版（对比参考，不走 Agent） |
| `skills/` | Agent 运行时加载的业务技能（会议纪要、图片分析） |
| `.opencode/commands/` | OpenCode 自定义命令（`/opsx-*` OpenSpec 工作流） |
| `.opencode/skills/` | OpenCode 技能（OpenSpec / Superpowers / Code Review） |
| `openspec/` | `openspec init` 后生成，OpenSpec 的提案与规格库 |
| `README.md` | 本文档（开发流程指南） |

---

## homework.zip密码
可以向授课老师索取 (miniclaw****)

---

## 学习检查清单

- [ ] 能说清为什么"先写 SPEC 再写代码"
- [ ] 知道 `.opencode/commands/` 与 `.opencode/skills/` 的目录约定，以及为什么要 `cd test6` 再启动 opencode
- [ ] 会用 `/opsx-propose` → `/opsx-apply` → `/opsx-archive` 走完一个 change
- [ ] 会在编码前用 brainstorming 讨论设计决策
- [ ] 会用 `requesting-code-review` 找缺陷并修复
- [ ] 能直接用 SPEC.md 一条 prompt 复现实现（方案 B），并说清两种方案的取舍
