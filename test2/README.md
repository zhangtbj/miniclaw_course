# Test2 — Agent 人设工程：用 backstory 塑造专家角色

## 学习目标

通过 `agent_character.py` 掌握 CrewAI Agent 的"人设工程"：

1. **Agent.kickoff()** — 直接与 Agent 交互，无需创建 Task 和 Crew
2. **backstory 设计** — 用角色背景定义 Agent 的专业能力、工作原则和输出风格
3. **自定义工具** — 通过 `IntermediateTool` 让 Agent 分步骤保存中间结论

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

---

## 运行

```bash
uv run python test2/agent_character.py
```

---

## 代码结构说明

```
agent_character.py
├── Agent 定义        → 配置角色、目标、背景故事、工具
└── kickoff 执行      → 传入用户消息，直接获取 Agent 回复
```

### Agent 定义

```python
agent = Agent(
    role="资深技术评审专家",
    goal="从架构、安全、性能、可维护性四个维度评审技术方案",
    backstory="你是一位拥有 15 年经验的资深架构师...",
    tools=[IntermediateTool()],
    llm=LoggedLLM(model=...),
    verbose=True,
)
```

| 参数 | 说明 |
|------|------|
| `role` | Agent 的角色身份，出现在 system prompt 中 |
| `goal` | Agent 的核心目标，决定其行为方向 |
| `backstory` | 背景故事，塑造 Agent 的专业能力、工作原则和输出风格 |
| `tools` | 可使用的自定义工具列表 |
| `llm` | 绑定的 LLM 实例，这里使用 `LoggedLLM` 打印请求日志 |
| `verbose=True` | 打印 Agent 内部的思考过程 |

### IntermediateTool

位于 `tools/intermediate_tool.py`，是一个 CrewAI 自定义工具：

- Agent 在多步推理时，调用此工具保存每一步的分析结论
- 防止长文本推理过程中"遗忘"中间结果
- 最终输出时可以回顾所有中间结论，组织更完整的答案

---

## 常见问题

**Q: `kickoff()` 和 `execute_task()` 有什么区别？**

`kickoff()` 是 Agent 的直接对话接口，传入 messages 即可获取回复，适合简单场景；`execute_task()` 需要通过 Task 对象描述任务，适合需要明确预期输出的场景。

**Q: backstory 对输出有什么影响？**

backstory 会被写入 system prompt，直接影响 Agent 的回答风格和专业深度。同样是"评审方案"，backstory 写"15年架构师"和"初级开发"会得到完全不同的评审质量。

**Q: 为什么需要 `LoggedLLM` 而不是 CrewAI 自带的 `LLM`？**

`LoggedLLM` 是我们自定义的 LLM 实现（位于 `llm/llm.py`），会在每次调用时打印完整的 system prompt、user prompt 和 API 响应，方便课程中观察 Agent 实际发送了什么内容。
