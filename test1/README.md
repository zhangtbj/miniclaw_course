# Test1 — CrewAI 基础入门

## 学习目标

通过 `basic_agent.py` 理解 CrewAI 的两个核心用法：

1. **LLM 直接调用** — 把 CrewAI 的 `LLM` 当作普通 API 客户端使用，不经过 Agent
2. **Agent 执行任务** — 配置 Agent 角色，将 LLM 交给 Agent 自主完成任务

---

## 前置准备

### 1. 配置 `.env`（项目根目录）

```env
OPENAI_MODEL=deepseek-v4-pro
OPENAI_API_KEY=sk-你的密钥
OPENAI_API_BASE=https://api.deepseek.com/v1
```

> 支持任何 OpenAI 兼容接口：DeepSeek、通义千问（DashScope）、GLM 等，只需更换 `model` 和 `base_url`。

### 2. 安装依赖

```bash
uv sync
```

---

## 运行

```bash
uv run python test1/basic_agent.py
```

---

## 代码结构说明

```
basic_agent.py
├── LLM 配置示例         → 创建 OpenAI 兼容的 LLM 实例
├── LLM 直接调用示例     → 不经过 Agent，直接调用 LLM
└── Agent 使用 LLM 示例  → Agent + Task 协同执行任务
```

### LLM 直接调用示例

```python
response = llm.call([{"role": "user", "content": prompt}])
```

- 等价于直接调用 OpenAI API，不经过任何 Agent 框架
- 适合简单的问答场景，无需 Agent 的推理循环

### Agent 使用 LLM 示例

```python
agent = Agent(role=..., goal=..., backstory=..., llm=llm)
task  = Task(description=..., expected_output=..., agent=agent)
result = agent.execute_task(task)
```

| 参数 | 说明 |
|------|------|
| `role` | Agent 的角色身份，影响 system prompt |
| `goal` | Agent 的目标，决定其行为方向 |
| `backstory` | 背景描述，塑造 Agent 的"人设" |
| `verbose=True` | 执行时打印思考过程，便于调试 |
| `expected_output` | 告诉 Agent 期望的输出格式 |

---

## 常见问题

**Q: LLM 直接调用和通过 Agent 调用有什么区别？**

直接调用是单次 API 请求，适合简单问答；Agent 可以多步思考、自我修正，适合复杂任务。

**Q: `verbose=True` 有什么用？**

开启后 Agent 会在控制台打印内部思考过程（Thought / Action / Observation），方便理解 Agent 是如何工作的。

**Q: 如何切换不同的 LLM？**

修改 `.env` 中的 `OPENAI_MODEL` 和 `OPENAI_API_BASE` 即可，代码无需改动。
