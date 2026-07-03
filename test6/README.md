# Test6 — 用开发 Skill 交付 MiniClaw WeLink 助理

本目录演示一条**业界主流的 AI 辅助开发流水线**：用三个开发 Skill 把一个想法变成经过审查的可运行代码。

```
想法/需求 ──OpenSpec──▶ SPEC.md（技术规格）
                            │
                            ▼
                     Superpowers：brainstorming → 开发实现
                            │
                            ▼
                       Code Review：审查 → 修复
                            │
                            ▼
                       welinkcli_agent.py（交付物）
```

> 本目录已预装相关 Skill（见 `test6/.opencode/skills/`）。`welinkcli_agent.py` 是按本流程产出的**参考实现**，`SPEC.md` 是它的实现契约。

---

## 三个 Skill 各做什么

| 阶段 | Skill | 输入 | 输出 | 解决的问题 |
|------|-------|------|------|-----------|
| ① 规格 | **OpenSpec**（`openspec-propose` 等） | 自然语言需求 | `SPEC.md` | 把"要做什么"变成"怎么做"的契约 |
| ② 开发 | **Superpowers**（`brainstorming` + `using-superpowers`） | `SPEC.md` | 实现代码 | 先想清楚再写，避免返工 |
| ③ 审查 | **Code Review**（`code-review-skill` / `/code-review`） | 实现代码 | 缺陷清单 + 修复 | 上线前兜底，抓 bug 与坏味道 |

---

## 阶段 ① 用 OpenSpec 生成 SPEC.md

### 为什么先写 SPEC？

直接让 AI 写代码，它只会写"大概对"的代码。先把需求固化为**实现契约**（接口签名、数据格式、错误处理、验收标准），后续每一步都有据可依，AI 也不容易跑偏。本目录的 [`SPEC.md`](SPEC.md) 就是这一步的产物——**仅凭它即可写出 `welinkcli_agent.py`**。

### 怎么做

OpenSpec 以"提案（proposal）"驱动，把需求拆成结构化规格。在 OpenCode / Claude Code 中调用 `openspec-propose`，给出需求：

```
openspec-propose

需求：开发一个 WeLink 群聊 AI 助理（welinkcli_agent.py，单文件）
- 通过 welink-cli（子进程）轮询群消息、发送回复
- 用 CrewAI Agent 生成回复，复用根目录 llm/llm.py 的 LoggedLLM
- 支持多模态（图片理解）和技能扩展（会议纪要、图片分析）
- 消息去重（持久化），不重复回复、不回复自身
- 配置走根目录 .env
```

随后用配套 Skill 推进：

- `openspec-apply-change` —— 把提案落成规格条目
- `openspec-sync-specs` —— 同步规格
- `openspec-explore` —— 浏览已有规格

### 产出要求

SPEC 至少要写清（对照 [`SPEC.md`](SPEC.md) 的章节）：

1. **外部接口契约**：welink-cli 的命令格式与返回 JSON 结构（`respData.chatInfo`、`msgId`、`serverSendTime`…）
2. **模块实现契约**：每个类/函数的签名、参数、返回值、异常处理
3. **关键规则**：去重逻辑、主循环过滤（过短/自身消息要先 `mark_replied` 再跳过）、排序（按时间降序）
4. **验收标准**：可逐条勾选的测试场景

---

## 阶段 ② 用 Superpowers 头脑风暴 + 开发

### 2.1 先 brainstorming，再动手

`brainstorming` Skill 的硬性要求：**任何创造性工作开始前，先讨论清楚再实现**。在编码前调用它，把 SPEC 里的开放决策聊透：

```
brainstorming

基于 SPEC.md，帮我讨论几个设计决策：
1. 单文件 vs 多文件：教学项目倾向单文件，用注释分块
2. 去重：持久化 JSON（支持重启恢复）vs 内存 set
3. 图片处理：先下载到本地再 base64，还是内存中转
4. 技能扩展：配置驱动 + 动态 Sub-Crew
```

brainstorming 会逐步追问、列 tradeoff，直到形成一个**你确认过的设计**，再进入实现。这一步能省掉后面大量返工。

### 2.2 按 SPEC 实现

设计定稿后，用 Superpowers 的开发类 Skill（`using-superpowers` / `executing-plans` / `subagent-driven-development`）按 SPEC 的模块布局逐步实现：

```
请按 SPEC.md 的"单文件模块布局"顺序实现 welinkcli_agent.py：
配置 → InboundMessage → 导入 LoggedLLM → AddImageTool →
SKILLS → SkillLoaderTool → create_main_agent → WeLink CLI 函数 →
RepliedTracker → handle_message/build_prompt → main()
```

要点（SPEC 已写死，实现时严格遵守）：
- LLM 用 `from llm.llm import LoggedLLM`，构造时**显式传 `model`**。
- `SkillLoaderTool.llm` 字段类型用 `Any`（避免 crewai 包装后 pydantic 校验失败）。
- 主循环过滤时，过短/自身消息要先 `mark_replied` 再 `continue`，否则队列卡死。

---

## 阶段 ③ 用 Code Review 审查并修复

### 审查

实现完成后，上线前过一遍 Code Review。两种用法：

- **Claude Code**：直接 `/code-review`（已内置），它会多角度扫描并产出结构化缺陷清单。
- **OpenCode Skill**：`requesting-code-review` / `code-review-skill`。

```
/code-review test6/welinkcli_agent.py
```

审查维度参考：

| 维度 | 本项目重点 |
|------|-----------|
| 正确性 | subprocess 超时、JSON 解析异常、`respData` 为 null、去重逻辑 |
| 健壮性 | 网络超时、文件 IO、LLM 失败不中断主循环 |
| 安全 | API Key 走环境变量不硬编码 |
| 可维护性 | 类型注解、docstring、模块边界 |

### 修复

把审查出的缺陷交回开发 Skill 修复，再用 `verification-before-completion` / `systematic-debugging` 验证，最后 `receiving-code-review` 复核。

> 本项目的 `welinkcli_agent.py` 已经过一轮 Code Review：修复了消息队列卡死、未排序、`respData` 为 null 崩溃、配置非整数启动崩溃等缺陷。

---

## 快速开始（运行参考实现）

```bash
# 1. 依赖
uv sync                          # 或 pip install -r requirements.txt

# 2. 配置根目录 .env（OPENAI_*、WELINK_GROUP_ID 等）

# 3. 确保 welink-cli 可用并已登录
welink-cli --version

# 4. 运行
uv run python test6/welinkcli_agent.py
```

在 WeLink 群里测试：发文本"帮我整理会议纪要"；发截图 + "看看这个报错"。

---

## 文件说明

| 文件 | 角色 |
|------|------|
| `SPEC.md` | 实现契约（阶段①产物，开发依据） |
| `welinkcli_agent.py` | 参考实现（阶段②③产物，CrewAI Agent 版） |
| `welinkcli_llm.py` | 直接 LLM 调用版（对比参考，不走 Agent） |
| `README.md` | 本文档（开发流程指南） |
| `.opencode/skills/` | 预装的开发 Skill（OpenSpec / Superpowers / Code Review） |

---

## 学习检查清单

- [ ] 能说清为什么"先写 SPEC 再写代码"
- [ ] 会用 OpenSpec 把需求转成带验收标准的 SPEC
- [ ] 会在编码前用 brainstorming 讨论设计决策
- [ ] 会用 `/code-review` 找缺陷并修复
- [ ] 能独立用这条流水线交付一个新模块
