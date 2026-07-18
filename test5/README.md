# Test5 — Skills 生态：动态加载技能

## 学习目标

通过 `agent_skills.py` 理解 CrewAI 的 Skills 生态架构：

1. **技能加载器（SkillLoaderTool）** — Agent 不直接持有所有工具，而是通过一个"元工具"按需加载子技能
2. **动态 Sub-Crew** — 每个技能是一个独立的 Sub-Crew，按需创建和执行
3. **可扩展性** — 新增技能只需在 `skills/` 下加一个 `SKILL.md`，无需改主代码

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
python test5/agent_skills.py
```

---

## 运行流程图

```
                   启动 agent_skills.py
                          │
                          ▼
   ┌───────────────────────────────────────────┐
   │ ① load_skills(test5/skills/)              │
   │   读 */SKILL.md → 解析 frontmatter        │
   │   meeting_summary / email_drafter /       │
   │   task_extractor                          │
   │ ② 创建 Agent                              │
   │   office_assistant                        │
   │   tools=[SkillLoaderTool(skills=SKILLS)]  │
   │   （Agent 只持有「技能加载器」，不直接持    │
   │    有全部工具）                            │
   └──────────────────┬────────────────────────┘
                      ▼
                   __main__
                      │
            ┌─────────┴──────────┐
            ▼                    ▼
    ┌──────────────┐      ┌──────────────┐
    │ demo_meeting │      │ demo_email   │
    ├──────────────┤      ├──────────────┤
    │ kickoff(     │      │ kickoff(     │
    │ "整理会议…") │      │  "写邮件…")  │
    │   │          │      │   │          │
    │   ▼          │      │   ▼          │
    │ 主 Agent     │      │ 主 Agent     │
    │ 推理 → 选技能 │      │ 推理 → 选技能 │
    │   │          │      │   │          │
    │   ▼          │      │   ▼          │
    │ skill_loader │      │ skill_loader │
    │("meeting_    │      │("email_      │
    │ summary")    │      │ drafter")    │
    │   │          │      │   │          │
    │   ▼          │      │   ▼          │
    │ 动态创建 Sub-Crew    │ 动态创建      │
    │ （专家 Agent+Task）  │ Sub-Crew     │
    │   │          │      │   │          │
    │   ▼          │      │   ▼          │
    │ 结构化 JSON  │      │ 结构化 JSON  │
    │ （会议纪要）  │      │ （邮件）     │
    │   │          │      │   │          │
    │   ▼          │      │   ▼          │
    │ 返回给用户   │      │ 返回给用户   │
    └──────────────┘      └──────────────┘
```

> 主 Agent 不直接干活：它只负责「选哪个技能」，选中后由 `SkillLoaderTool` 动态创建一个一次性 Sub-Crew 执行技能，返回结构化结果再交给用户。

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
├── load_skills()     → 扫描 skills/*/SKILL.md，解析 frontmatter
├── Agent 定义         → 办公小助手，配备 SkillLoaderTool
├── 场景1              → 整理会议纪要（调用 meeting_summary 技能）
└── 场景2              → 撰写商务邮件（调用 email_drafter 技能）

skills/
├── meeting_summary/SKILL.md   → 会议纪要技能（frontmatter + 操作指引）
├── email_drafter/SKILL.md     → 商务邮件技能
└── task_extractor/SKILL.md    → 待办提取技能
```

### 技能配置：SKILL.md 文件

每个技能是 `skills/` 下的一个子目录，核心是 `SKILL.md`：YAML frontmatter 声明元信息，正文写操作指引（和 test6 的真实 skill 同一套格式）。

```
skills/
├── meeting_summary/SKILL.md
├── email_drafter/SKILL.md
└── task_extractor/SKILL.md
```

以 `skills/meeting_summary/SKILL.md` 为例：

```markdown
---
name: meeting_summary
description: 将杂乱的会议记录整理为结构化纪要   ← LLM 据此选技能（仅这两个字段）
---

# 会议纪要整理          ← 正文作为操作指引注入子 Agent
## 处理步骤
1. 提取参会人 ...
2. 提炼关键决策 ...

## 输出要求            ← 输出格式直接写在正文里
- attendees：参会人列表
- key_decisions：关键决策
- action_items：待办事项
```

frontmatter 只有两个字段（标准 skill 格式）：
- `name`：技能标识符
- `description`：技能描述（LLM 据此选择技能）

> 输入 / 输出格式不放在 frontmatter，而是写进正文，子 Agent 读正文就知道该怎么处理、返回什么。

### 通过读文件加载

`agent_skills.py` 不再把技能写死在数组里，而是扫描目录读文件：

```python
def load_skills(skills_dir: Path) -> list[dict]:
    skills = []
    for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
        text = skill_file.read_text(encoding="utf-8")
        # 用正则拆出 YAML frontmatter 与 markdown 正文
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
        meta = yaml.safe_load(m.group(1))
        skills.append({
            "name": meta["name"],
            "description": meta["description"],
            "instructions": m.group(2).strip(),   # 正文：子 Agent 的操作指引（含输出格式）
        })
    return skills

SKILLS = load_skills(Path(__file__).parent / "skills")
```

加载后仍是同样的 `list[dict]`，`SkillLoaderTool(skills=SKILLS)` 用法不变；新增的 `instructions` 字段会被 `SkillLoaderTool` 注入子 Agent 的任务描述。

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
    - skill_task（操作指引 + 会议记录作为输入）
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

在 `skills/` 下新建一个子目录，放一个 `SKILL.md` 即可，主代码完全不用改：

```
skills/new_skill/SKILL.md
```

```markdown
---
name: new_skill
description: 新技能的描述
---

# 新技能
（处理步骤 + 输出要求都写在正文里）
```

下次启动 `load_skills()` 会自动扫到它。

**Q: Sub-Crew 是什么？**

Sub-Crew 是动态创建的独立 Crew，每个技能执行时都会创建一个新的 Sub-Crew。它有自己的 Agent 和 Task，执行完毕后销毁。

**Q: 为什么要把 LLM 传给 SkillLoaderTool？**

Sub-Crew 需要使用和主 Agent 相同的 LLM 配置。通过 `SkillLoaderTool(skills=SKILLS, llm=llm)` 传递，确保 Sub-Crew 使用正确的模型。
