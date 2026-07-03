# Test4 — Agent 工具调用：让 Agent 操作外部世界

## 学习目标

通过 `agent_tools.py` 理解 CrewAI 的工具（Tools）机制：

1. **工具调用** — Agent 不再只是"说话"，而是能读写文件、操作外部系统
2. **工具选择** — Agent 根据任务自主决定使用哪个工具、何时使用
3. **状态持久化** — 多轮对话通过文件系统共享状态

---

## 前置准备

### 1. 配置 `.env`（项目根目录）

```env
OPENAI_MODEL=auto
OPENAI_API_KEY=你的密钥
OPENAI_API_BASE=http://xiaoluban.rnd.huawei.com:80/y/llm/v1
```

### 2. 安装依赖

```bash
uv sync
```

> 需要 `crewai-tools` 包（已包含在 pyproject.toml 中）

---

## 运行

```bash
uv run python test4/agent_tools.py
```

---

## 核心概念：Agent 的"手"

前三个 test 的 Agent 只能生成文本（"大脑"），test4 的 Agent 能操作文件（"手"）：

| Test | Agent 能力 | 类比 |
|------|-----------|------|
| test1-3 | 生成文本 | 只能说话 |
| **test4** | **读写文件** | **能动手操作** |

---

## 代码结构说明

```
agent_tools.py
├── Agent 定义     → 笔记助手，配备 FileWriterTool + FileReadTool
├── Task 定义      → 根据用户输入执行操作
└── 两轮对话       → 记笔记（写文件）→ 查笔记（读文件）
```

### 给 Agent 配备工具

```python
from crewai_tools import FileWriterTool, FileReadTool

note_agent = Agent(
    role="笔记助手",
    tools=[FileWriterTool(), FileReadTool()],  # ← 关键：给 Agent 工具
    ...
)
```

Agent 会根据任务**自主决定**使用哪个工具：
- 用户说"帮我记一下" → Agent 调用 `FileWriterTool` 写入文件
- 用户说"查一下我记了什么" → Agent 调用 `FileReadTool` 读取文件

### 多轮对话：通过文件持久化状态

```python
# 第一轮：Agent 写入 notes.md
crew.kickoff(inputs={"user_input": "帮我记三条：..."})

# 第二轮：Agent 读取 notes.md
crew.kickoff(inputs={"user_input": "我记了哪些事情？"})
```

每轮 `kickoff` 是独立的 LLM 调用，但通过文件系统共享状态。

---

## 运行输出示例

```
第一轮：记笔记
🔧 Tool Execution: file_writer_tool
   写入 notes.md
结果：已帮你记录 3 条笔记...

第二轮：查笔记
🔧 Tool Execution: read_a_files_content
   读取 notes.md
结果：你记了以下事项：1）明天下午3点开会...
```

---

## CrewAI 内置工具

CrewAI 提供了多种开箱即用的工具：

| 工具 | 用途 |
|------|------|
| `FileWriterTool` | 写入文件 |
| `FileReadTool` | 读取文件 |
| `ScrapeWebsiteTool` | 抓取网页内容 |
| `DirectoryReadTool` | 列出目录内容 |
| `SerperDevTool` | 搜索引擎查询 |

更多工具见 [crewai-tools 文档](https://github.com/crewAIInc/crewAI-tools)

---

## 常见问题

**Q: Agent 怎么知道该用哪个工具？**

工具的描述（description）会被写入 system prompt，LLM 根据任务内容和工具描述自行判断。你在 verbose 输出中能看到 Agent 的"思考过程"。

**Q: 可以自己写工具吗？**

可以。继承 `crewai.tools.BaseTool`，实现 `_run()` 方法即可。参考 `tools/intermediate_tool.py`。

**Q: Agent 一次能用多个工具吗？**

可以。Agent 会在一轮对话中多次调用工具（如先读文件、再写文件），直到完成任务。
