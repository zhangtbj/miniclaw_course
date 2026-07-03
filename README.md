# MiniClaw 实战用户手册

> 从零构建 AI Agent 应用 — 基于 CrewAI 的完整学习路径

---

## 项目简介

MiniClaw 是一个**渐进式 AI Agent 开发课程**，通过 6 个递进的实战模块，带你从 LLM 基础调用到完整的 WeLink AI 助理开发。

**你将学到**：
- LLM 调用与日志调试
- Agent 人设工程（backstory）
- 多任务链式工作流
- 工具调用（文件读写、网络请求）
- Skills 生态系统
- WeLink 集成 + 多模态理解
- 使用业界开发 Skill 加速开发

---

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repo-url>
cd MiniClaw

# 安装依赖（二选一）

# 方式 A：uv（推荐，自动管理虚拟环境）
uv sync

# 方式 B：pip + venv
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 API Key
```

### 2. 配置 LLM 与 WeLink

编辑 `.env` 文件（参考 `.env.example`）：

```env
# LLM 配置（默认使用内部小鲁班网关，支持任何 OpenAI 兼容接口）
OPENAI_MODEL=auto                      # auto 对应 Qwen-V3.5-35B-A3B（支持多模态）
OPENAI_API_KEY=你的密钥                  # 向小鲁班发送"获取apikey"获取
OPENAI_API_BASE=http://xiaoluban.rnd.huawei.com:80/y/llm/v1
OTEL_SDK_DISABLED=true
NO_PROXY=xiaoluban.rnd.huawei.com

# WeLink 配置（test6 需要）
WELINK_GROUP_ID=your-group-id-here     # 从群配置获取
CHECK_INTERVAL=10
RECENT_MINUTES=10
```

**支持的 LLM 提供商**：
- 小鲁班（内部默认，model 设为 `auto`）
- DeepSeek / 通义千问（阿里云 DashScope）/ OpenAI / 智谱 GLM
- 其他 OpenAI 兼容接口（更换 `model` 和 `base_url` 即可）

> test1-5 只需 LLM 配置；test6 还需 WeLink 配置并安装 `welink-cli`。所有脚本通过 `load_dotenv` 自动读取根目录 `.env`。

### 3. 运行第一个示例

```bash
# test1: LLM 直接调用
uv run python test1/basic_agent.py

# test2: Agent 人设工程
uv run python test2/agent_character.py

# test3: 多任务链式工作流
uv run python test3/agent_task.py
```

---

## 学习路径

### 📚 模块总览

```
test1  LLM 基础         → 学会调用 LLM，理解 system/user prompt
  ↓
test2  Agent 人设       → 用 backstory 塑造专家角色
  ↓
test3  Task 链式工作流  → 多任务协作，结构化输出
  ↓
test4  工具调用         → Agent 操作外部世界（文件、网络）
  ↓
test5  Skills 生态      → 动态加载技能，可扩展架构
  ↓
test6  项目实战         → WeLink AI 助理 + 开发 Skill
```

---

### 🎯 模块详解

#### Test1 — LLM 基础调用

**学习目标**：理解 LLM 的两种调用方式

| 内容 | 文件 | 说明 |
|------|------|------|
| LLM 直接调用 | `basic_agent.py` | 不经过 Agent，直接调用 LLM |
| Agent 调用 | `basic_agent.py` | 通过 Agent 执行任务 |
| 日志拦截 | `basic_claw.py`（test2） | 观察 system/user prompt |

**运行**：
```bash
uv run python test1/basic_agent.py
```

**核心代码**：
```python
from crewai import LLM

llm = LLM(
    model=os.getenv("OPENAI_MODEL"),
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_API_BASE"),
)

# 直接调用
response = llm.call([{"role": "user", "content": "你好"}])
```

📖 **详细文档**：[test1/README.md](test1/README.md)

---

#### Test2 — Agent 人设工程

**学习目标**：用 backstory 塑造 Agent 的专业能力

| 内容 | 文件 | 说明 |
|------|------|------|
| Agent.kickoff() | `agent_character.py` | 直接与 Agent 对话 |
| backstory 设计 | `agent_character.py` | 定义角色、工作原则、输出风格 |
| IntermediateTool | `agent_character.py` | 保存中间思考结果 |

**运行**：
```bash
uv run python test2/agent_character.py
```

**核心代码**：
```python
agent = Agent(
    role='资深技术评审专家',
    goal='从架构、安全、性能、可维护性四个维度评审技术方案',
    backstory="""
    你是一位拥有 15 年经验的资深架构师...
    **工作原则**：
    - 每个问题要说明"为什么是问题"和"建议怎么改"
    - 按严重程度分级：🔴 阻塞性 / 🟡 建议优化 / 🟢 锦上添花
    """,
    tools=[IntermediateTool()],
    llm=LoggedLLM(model=...),
)

result = agent.kickoff(messages)
```

📖 **详细文档**：[test2/README.md](test2/README.md)

---

#### Test3 — Task 链式工作流

**学习目标**：多任务协作 + Pydantic 结构化输出

| 内容 | 文件 | 说明 |
|------|------|------|
| Bug 报告生成 | `agent_task.py` | Task 1: 生成 Bug 报告 |
| 根因分析 | `agent_task.py` | Task 2: 分析技术根因 |
| 修复方案 | `agent_task.py` | Task 3: 给出修复建议 |
| Pydantic 模型 | `agent_task.py` | 强制输出结构化 JSON |

**运行**：
```bash
uv run python test3/agent_task.py
```

**核心代码**：
```python
# 定义 Pydantic 模型
class BugReport(BaseModel):
    title: str
    severity: str
    reproduction_steps: List[str]

# 定义 Task
task1 = Task(
    description="根据用户反馈生成 Bug 报告",
    output_pydantic=BugReport,
    agent=qa_expert,
)

task2 = Task(
    description="分析 Bug 的技术根因",
    output_pydantic=RootCauseReport,
    agent=tech_lead,
    context=[task1],  # 接收 Task 1 的输出
)

# 执行
crew = Crew(tasks=[task1, task2, task3], process=Process.sequential)
result = crew.kickoff()
```

📖 **详细文档**：[test3/README.md](test3/README.md)

---

#### Test4 — 工具调用

**学习目标**：Agent 操作外部世界（文件读写）

| 内容 | 文件 | 说明 |
|------|------|------|
| 笔记助手 | `agent_tools.py` | 使用 FileWriterTool / FileReadTool |
| 多轮对话 | `agent_tools.py` | 通过文件持久化状态 |

**运行**：
```bash
uv run python test4/agent_tools.py
```

**核心代码**：
```python
from crewai_tools import FileWriterTool, FileReadTool

agent = Agent(
    role="笔记助手",
    tools=[FileWriterTool(), FileReadTool()],  # 给 Agent 工具
    ...
)

# Agent 自主决定何时读文件、何时写文件
crew.kickoff(inputs={"user_input": "帮我记三条：..."})
crew.kickoff(inputs={"user_input": "我记了哪些？"})
```

📖 **详细文档**：[test4/README.md](test4/README.md)

---

#### Test5 — Skills 生态系统

**学习目标**：动态加载技能，可扩展架构

| 内容 | 文件 | 说明 |
|------|------|------|
| 办公小助手 | `agent_skills.py` | 3 个办公技能 |
| SkillLoaderTool | `tools/skill_loader_tool.py` | 技能加载器 |
| Sub-Crew | `tools/skill_loader_tool.py` | 动态创建子 Crew |

**运行**：
```bash
uv run python test5/agent_skills.py
```

**核心代码**：
```python
# 定义技能
SKILLS = [
    {
        "name": "meeting_summary",
        "description": "整理会议纪要",
        "input_schema": {"raw_notes": "原始记录"},
        "output_schema": {"attendees": "...", "action_items": "..."}
    }
]

# Agent 只配备技能加载器
agent = Agent(
    tools=[SkillLoaderTool(skills=SKILLS, llm=llm)],
    ...
)

# Agent 根据需求自动选择技能
crew.kickoff(inputs={"user_input": "帮我整理会议记录"})
```

📖 **详细文档**：[test5/README.md](test5/README.md)

---

#### Test6 — 项目实战：WeLink AI 助理

**学习目标**：完整项目开发 + 使用业界开发 Skill

| 内容 | 文件 | 说明 |
|------|------|------|
| CrewAI Agent 版（主） | `welinkcli_agent.py` | 单文件，集成轮询/Agent/工具/技能 |
| 直接 LLM 调用版 | `welinkcli_llm.py` | 对比参考，无 Agent 框架 |
| 技术规范 | `SPEC.md` | 项目架构与模块定义 |
| 开发指南 | `test6/README.md` | OpenSpec / SuperPowers / Code Review 工作流 |

**运行**：
```bash
# 需先配置 WELINK_GROUP_ID 并确保 welink-cli 可用
uv run python test6/welinkcli_agent.py
```

**学习重点**：
- 阅读 SPEC.md 理解单文件完整架构
- 使用 OpenSpec 生成需求规格
- 使用 SuperPowers 进行 brainstorming 和实现
- 使用 Code Review 审查代码

📖 **详细文档**：[test6/README.md](test6/README.md) | [SPEC.md](test6/SPEC.md)

---

## 项目结构

```
MiniClaw/
├── README.md              # 本文件（用户手册）
├── pyproject.toml         # 依赖管理（uv）
├── requirements.txt       # 依赖清单（pip）
├── uv.lock                # 依赖锁定（uv）
├── .env.example           # 环境变量模板
├── .env                   # 环境变量（需创建，已 gitignore）
│
├── llm/                   # 自定义 LLM
│   ├── __init__.py
│   └── llm.py             # LoggedLLM（带日志拦截）
│
├── tools/                 # 自定义工具
│   ├── __init__.py
│   ├── intermediate_tool.py    # 中间结果保存
│   └── skill_loader_tool.py    # 技能加载器
│
├── test1/                 # LLM 基础
│   ├── README.md
│   └── basic_agent.py
│
├── test2/                 # Agent 人设
│   ├── README.md
│   └── agent_character.py
│
├── test3/                 # Task 链式工作流
│   ├── README.md
│   └── agent_task.py
│
├── test4/                 # 工具调用
│   ├── README.md
│   └── agent_tools.py
│
├── test5/                 # Skills 生态
│   ├── README.md
│   └── agent_skills.py
│
└── test6/                 # 项目实战：WeLink AI 助理
    ├── README.md              # 开发指南（开发 Skill 工作流）
    ├── SPEC.md                # 技术规范
    ├── welinkcli_agent.py    # CrewAI Agent 版（单文件，主版本）
    └── welinkcli_llm.py       # 直接 LLM 调用版（对比参考）
```

---

## 核心组件

### LoggedLLM

自定义 LLM 实现，**打印完整的 system/user prompt**，方便调试和学习。

```python
from llm.llm import LoggedLLM

llm = LoggedLLM(
    model=os.getenv("OPENAI_MODEL"),
)

# 运行时会自动打印：
# 🔍 发送给 LLM 的消息 (共 2 条)
# --- [1] role: system ---
# You are 资深技术评审专家...
# --- [2] role: user ---
# 请对以下技术方案进行评审...
```

**功能**：
- ✅ 请求日志（system/user prompt 打印）
- ✅ 重试机制（5xx / 429 / 超时）
- ✅ 空内容重试
- ✅ 异步 `acall()`
- ✅ Function Calling
- ✅ 多模态图片支持

📖 **源码**：[llm/llm.py](llm/llm.py)

---

### IntermediateTool

Agent 中间结果保存工具，防止长文本推理过程中"遗忘"。

```python
from tools.intermediate_tool import IntermediateTool

agent = Agent(
    tools=[IntermediateTool()],
    ...
)

# Agent 在多步推理时，调用此工具保存每一步的分析结论
```

📖 **源码**：[tools/intermediate_tool.py](tools/intermediate_tool.py)

---

### SkillLoaderTool

技能加载器，实现 Skills 生态系统。

```python
from tools.skill_loader_tool import SkillLoaderTool

agent = Agent(
    tools=[SkillLoaderTool(skills=SKILLS, llm=llm)],
    ...
)

# Agent 根据需求自动选择技能，动态创建 Sub-Crew 执行
```

📖 **源码**：[tools/skill_loader_tool.py](tools/skill_loader_tool.py)

---

## 常见问题

### Q: 需要安装 uv 吗？

推荐安装。uv 是快速的 Python 包管理器，比 pip 快 10-100 倍。

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

如果不想用 uv，也可以用 pip（项目已提供 `requirements.txt`）：

```bash
python3.11 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt      # 安装
pip install --upgrade -r requirements.txt  # 更新依赖
```

> uv 用 `uv sync` 安装/更新；pip 用 `pip install -r requirements.txt`，更新时重新执行同一命令（可加 `--upgrade`）。

---

### Q: 为什么默认用小鲁班？还能换别的 LLM 吗？

本课程默认使用内部 **小鲁班** LLM 网关（`OPENAI_API_BASE` 指向 `xiaoluban.rnd.huawei.com`），`OPENAI_MODEL=auto` 对应 Qwen-V3.5-35B-A3B（支持多模态）。API Key 向小鲁班发送"获取apikey"即可获得。

由于代码走的是 **OpenAI 兼容接口**，只需修改 `.env` 中的 `model` 和 `base_url` 即可切换到 DeepSeek、通义千问、OpenAI、智谱 GLM 等。

---

### Q: test1-5 的代码可以直接运行吗？

可以。每个 test 都是独立的，不依赖其他 test。

```bash
# 按顺序运行
uv run python test1/basic_agent.py
uv run python test2/agent_character.py
uv run python test3/agent_task.py
uv run python test4/agent_tools.py
uv run python test5/agent_skills.py
```

---

### Q: test6 的代码在哪里？

test6 是项目实战模块，已提供完整可运行的代码：

- `welinkcli_agent.py` — CrewAI Agent 版（单文件，主版本），集成消息轮询、Agent 推理、工具调用、技能加载
- `welinkcli_llm.py` — 直接 LLM 调用版（对比参考，无 Agent 框架）

```bash
# 运行前需配置 WELINK_GROUP_ID，并确保 welink-cli 已安装登录
uv run python test6/welinkcli_agent.py
```

阅读 [test6/SPEC.md](test6/SPEC.md) 理解架构，参考 [test6/README.md](test6/README.md) 体验用 OpenSpec / SuperPowers / Code Review 的开发流程。

---

### Q: 如何调试 Agent 的行为？

设置 `verbose=True` 查看 Agent 的思考过程：

```python
agent = Agent(
    ...
    verbose=True,  # 打印思考过程
)
```

使用 `LoggedLLM` 查看 LLM 请求：

```python
llm = LoggedLLM(model=...)
# 自动打印 system/user prompt
```

---

## 进阶学习

### 1. 自定义工具

继承 `crewai.tools.BaseTool`，实现 `_run()` 方法：

```python
from crewai.tools import BaseTool

class MyTool(BaseTool):
    name: str = "my_tool"
    description: str = "工具描述"

    def _run(self, input: str) -> str:
        # 实现逻辑
        return "结果"
```

---

### 2. 自定义技能

在 `SKILLS` 列表中添加配置：

```python
SKILLS = [
    {
        "name": "my_skill",
        "description": "技能描述",
        "input_schema": {...},
        "output_schema": {...}
    }
]
```

---

### 3. 多模态支持

使用 `AddImageTool` 加载图片（test6 中内置于 `welinkcli_agent.py`）：

```python
from crewai.tools import BaseTool

class AddImageTool(BaseTool):
    name: str = "add_image"
    # 将本地图片转为 base64 data URI，供多模态 LLM 理解
    ...
```

📖 **源码**：[test6/welinkcli_agent.py](test6/welinkcli_agent.py) 中的 `AddImageTool`

---

## 参考资源

### CrewAI 官方文档
- [CrewAI Docs](https://docs.crewai.com/)
- [CrewAI GitHub](https://github.com/crewAIInc/crewAI)
- [crewai-tools](https://github.com/crewAIInc/crewAI-tools)

### 开发 Skill
- **OpenSpec**：从需求文档生成代码框架
- **SuperPowers**：增强代码生成能力
- **CodeReviewer**：自动代码审查
- **understand-anything**：理解代码库（Claude Code 内置）

### WeLink CLI
- WeLink CLI（`welink-cli`）：用于群消息收发，需在本地安装并 `welink-cli login` 登录
- 常用命令：`im query-history-message`（拉取历史消息）、`im send-to-group`（发送群消息）

---

## 学习建议

### 推荐的学习顺序

1. **先跑通**：按顺序运行 test1-5，观察输出
2. **再读码**：阅读每个 test 的 README.md，理解核心概念
3. **后修改**：尝试修改 backstory、Task description，观察效果
4. **终实战**：阅读 [test6/SPEC.md](test6/SPEC.md)，运行并修改 WeLink AI 助理

### 关键概念速查

| 概念 | 出处 | 一句话解释 |
|------|------|-----------|
| LLM | test1 | 大语言模型，AI 的"大脑" |
| Agent | test2 | 有角色的 LLM，AI 的"人设" |
| Task | test3 | Agent 要完成的任务 |
| Tool | test4 | Agent 可以调用的外部工具 |
| Skill | test5 | 动态加载的子 Crew |
| Crew | test3 | Agent + Task 的组合 |
| Process | test3 | 任务执行流程（sequential/hierarchical） |

---

## 许可证

MIT License

---

## 联系方式

如有问题，请联系课程助教或提交 Issue。
