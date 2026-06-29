# Test5 — Skills 生态：动态加载技能

## 学习目标

通过 `agent_skills.py` 理解 CrewAI 的 Skills 生态架构：

1. **技能加载器（SkillLoaderTool）** — Agent 不直接持有所有工具，而是通过一个"元工具"按需加载子技能
2. **动态 Sub-Crew** — 每个技能是一个独立的 Sub-Crew，按需创建和执行
3. **可扩展性** — 新增技能只需添加配置，无需修改主代码

---

## 前置准备

### 1. 配置 `.env`（项目根目录）

```env
OPENAI_MODEL=deepseek-v4-pro
OPENAI_API_KEY=sk-你的密钥
OPENAI_API_BASE=https://api.deepseek.com/v1
```

### 2. 安装依赖

```bash
uv sync
```

---

## 运行

```bash
uv run python test5/agent_skills.py
```

---

## 核心概念：Skills 生态 vs 直接配备工具

### 传统方式（test4）

```python
agent = Agent(
    tools=[FileWriterTool(), FileReadTool()]  # 直接配备所有工具
)
```

**问题**：工具多了 → system prompt 爆炸 → LLM 选择困难

### Skills 生态（test5）

```python
agent = Agent(
    tools=[SkillLoaderTool(skills=SKILLS)]  # 只配备一个"技能加载器"
)
```

**优势**：Agent 按需加载技能，可扩展性强

---

## 代码结构说明

```
agent_skills.py
├── SKILLS 定义        → 3 个办公技能的配置
├── Agent 定义         → 办公小助手，配备 SkillLoaderTool
├── 场景1              → 整理会议纪要（调用 meeting_summary 技能）
└── 场景2              → 撰写商务邮件（调用 email_drafter 技能）
```

### 技能配置

```python
SKILLS = [
    {
        "name": "meeting_summary",
        "type": "task",
        "description": "将杂乱的会议记录整理为结构化纪要",
        "input_schema": {"raw_notes": "原始会议记录文本"},
        "output_schema": {
            "attendees": "参会人列表",
            "key_decisions": "关键决策",
            "action_items": "待办事项"
        }
    },
    # ... 其他技能
]
```

每个技能包含：
- `name`：技能标识符
- `description`：技能描述（LLM 据此选择技能）
- `input_schema`：输入参数说明
- `output_schema`：输出格式定义

### SkillLoaderTool 工作流程

```
用户请求："帮我整理会议记录"
    ↓
主 Agent 看到可用技能列表
    ↓
LLM 推理：用户要整理会议 → 选择 meeting_summary
    ↓
调用 skill_loader(skill_name="meeting_summary", skill_input="...")
    ↓
SkillLoaderTool 创建 Sub-Crew：
    - skill_agent（meeting_summary 专家）
    - skill_task（处理会议记录）
    ↓
Sub-Crew 执行，返回结构化 JSON
    ↓
主 Agent 收到结果，返回给用户
```

---

## 运行输出示例

### 场景1：会议纪要

```
🔧 加载技能：meeting_summary
   输入：今天下午3点开了产品评审会...

技能返回：
{
  "attendees": "产品张三、开发李四、设计王五",
  "key_decisions": "决定先上线用户反馈最多的深色模式",
  "action_items": "李四开发需要两周；王五下周一前交付设计稿；..."
}
```

### 场景2：商务邮件

```
🔧 加载技能：email_drafter
   输入：收件人：张总；主题：项目延期通知...

技能返回：
{
  "subject": "项目延期交付通知",
  "body": "张总，您好！鉴于近期项目需求发生变更..."
}
```

---

## Agent 如何选择技能？

Agent 的 system prompt 中包含技能列表：

```
可用技能：
- meeting_summary: 将杂乱的会议记录整理为结构化纪要
- email_drafter: 根据要点生成专业的商务邮件
- task_extractor: 从文本中提取待办任务
```

LLM 根据用户需求匹配最合适的技能：
- "整理会议记录" → `meeting_summary`
- "写一封邮件" → `email_drafter`
- "提取待办任务" → `task_extractor`

**关键点**：技能的 `description` 越清晰，LLM 选择越准确。

---

## 常见问题

**Q: 和 test4 的工具调用有什么区别？**

test4 是 Agent 直接调用工具（如 FileReadTool）；test5 是 Agent 调用"技能加载器"，由加载器创建 Sub-Crew 执行技能。Skills 生态更适合工具数量多的场景。

**Q: 如何新增一个技能？**

只需在 `SKILLS` 列表中添加配置即可，无需修改主代码：

```python
SKILLS.append({
    "name": "new_skill",
    "description": "新技能的描述",
    "input_schema": {...},
    "output_schema": {...}
})
```

**Q: Sub-Crew 是什么？**

Sub-Crew 是动态创建的独立 Crew，每个技能执行时都会创建一个新的 Sub-Crew。它有自己的 Agent 和 Task，执行完毕后销毁。

**Q: 为什么要把 LLM 传给 SkillLoaderTool？**

Sub-Crew 需要使用和主 Agent 相同的 LLM 配置。通过 `SkillLoaderTool(skills=SKILLS, llm=llm)` 传递，确保 Sub-Crew 使用正确的模型。
