# Test3 — Task 链式工作流：多任务协作与结构化输出

## 学习目标

通过 `agent_task.py` 掌握 CrewAI 的多任务链式工作流：

1. **Task 链式执行** — 三个 Task 按依赖关系顺序执行，上游输出自动传递给下游
2. **Pydantic 结构化输出** — 用 `output_pydantic` 强制 LLM 输出结构化 JSON，而非自由文本
3. **结果访问** — 通过 `result.pydantic`、`result.raw`、`result.tasks_output` 获取不同粒度的输出

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
pip install -r requirements.txt        # 在根目录 .venv 中执行
```

---

## 运行

```bash
python test3/agent_task.py
```

---

## 运行流程图

```
                   启动 agent_task.py
                          │
                          ▼
   ┌─────────────────────────────────────────┐
   │ ① 定义 Pydantic 输出模型                │
   │   BugReport / RootCauseReport /         │
   │   FixSuggestionReport                   │
   └──────────────────┬──────────────────────┘
                      ▼
   ┌─────────────────────────────────────────┐
   │ ② 创建 Agent                            │
   │   qa_expert（资深测试工程师）            │
   │   tech_lead（技术负责人）                │
   └──────────────────┬──────────────────────┘
                      ▼
   ┌─────────────────────────────────────────┐
   │ ③ 创建 3 个 Task（用 context 建立依赖）  │
   └──────────────────┬──────────────────────┘
                      ▼
   ┌─────────────────────────────────────────┐
   │ ④ Crew(process=sequential)              │
   │   crew.kickoff(inputs={"bug_description"│
   │                        : bug_input})    │
   └──────────────────┬──────────────────────┘
                      ▼
   ┌──────────────────────────────────────────────────┐
   │         顺序执行（上游输出 → 下游 context）        │
   │                                                  │
   │  Task1  bug_report_task                          │
   │   qa_expert ──▶ BugReport                        │
   │                    │                             │
   │                    ▼ context                     │
   │  Task2  root_cause_task                          │
   │   tech_lead ──▶ RootCauseReport                  │
   │                    │                             │
   │                    ▼ context（Task1 + Task2）    │
   │  Task3  fix_suggestion_task                      │
   │   tech_lead ──▶ FixSuggestionReport              │
   └────────────────────┬─────────────────────────────┘
                        ▼
   ┌─────────────────────────────────────────┐
   │ ⑤ 输出结果                              │
   │   result.raw          最终 Task 原始文本 │
   │   result.pydantic     最终结构化对象     │
   │   result.tasks_output 每个 Task 的输出   │
   └─────────────────────────────────────────┘
```

> 三个 Task 按声明顺序串行；每个 Task 用 `output_pydantic` 强制结构化输出，下游通过 `context` 自动接收上游结果。

---

## 代码结构说明

```
agent_task.py
├── Pydantic 模型定义   → BugReport / RootCauseReport / FixSuggestionReport
├── Agent 定义          → qa_expert（测试工程师）+ tech_lead（技术负责人）
├── Task 定义           → 三个 Task，通过 context 链式传递
├── Crew 执行           → Process.sequential 顺序执行
└── 结果输出            → 访问结构化数据和每个任务的独立输出
```

### 三任务链式流程

```
┌──────────────────┐     context      ┌──────────────────┐     context      ┌──────────────────┐
│  bug_report_task  │ ──────────────▶ │  root_cause_task  │ ──────────────▶ │ fix_suggestion   │
│  agent=qa_expert  │                 │  agent=tech_lead   │                 │ agent=tech_lead  │
│  → BugReport      │                 │  → RootCauseReport │                 │ → FixSuggestion  │
└──────────────────┘                  └──────────────────┘                  └──────────────────┘
```

### Task 之间的数据传递

```python
root_cause_task = Task(
    ...
    context=[bug_report_task],                    # 接收 Task 1 的输出
)

fix_suggestion_task = Task(
    ...
    context=[bug_report_task, root_cause_task],   # 接收 Task 1 + Task 2 的输出
)
```

`context` 参数告诉 CrewAI：执行这个 Task 时，把上游 Task 的输出注入到 prompt 中。

### Agent 分配

每个 Task 通过 `agent=` 参数显式指定由哪个 Agent 执行：

| Task | Agent | 职责 |
|------|-------|------|
| bug_report_task | qa_expert | 将口头描述转为标准 Bug 报告 |
| root_cause_task | tech_lead | 多层面根因分析 |
| fix_suggestion_task | tech_lead | 修复方案对比与推荐 |

Crew 的 `agents=` 列表只是"团队花名册"，不决定谁做什么。

### Pydantic 结构化输出

```python
class BugReport(BaseModel):
    title: str = Field(..., description="Bug 标题")
    severity: str = Field(..., description="严重等级")
    reproduction_steps: List[str] = Field(..., description="复现步骤")
    ...

bug_report_task = Task(
    ...
    output_pydantic=BugReport,   # 强制输出匹配此模型
)
```

`output_pydantic` 让 CrewAI 在 LLM 返回后自动校验并解析为 Pydantic 对象，下游代码可以直接用 `result.pydantic.title` 访问字段。

---

## 输出访问方式

```python
result.raw                          # 最终 Task 的原始文本
result.pydantic                     # 最终 Task 的 Pydantic 对象
result.pydantic.recommendation      # 直接访问字段
result.tasks_output                 # 所有 Task 的输出列表
result.tasks_output[0].pydantic     # 第一个 Task 的 Pydantic 对象
```

---

## 常见问题

**Q: Crew 怎么知道哪个 Task 该由哪个 Agent 执行？**

每个 Task 的 `agent=` 参数显式指定了执行者，Crew 不做自动分配。

**Q: `context` 和 `inputs` 有什么区别？**

- `inputs`：从外部传入 Crew 的初始数据（如用户输入的 Bug 描述）
- `context`：Task 之间自动传递的上游输出

**Q: 如果去掉 `Process.sequential` 会怎样？**

CrewAI 默认就是 sequential 模式，显式写上是为了代码可读性。另一个可选模式是 `Process.hierarchical`（层级模式），由一个 manager Agent 动态分配任务。
