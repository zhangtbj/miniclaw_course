# MiniClaw WeLink CLI AI 助理 — 技术规范

## 项目概述

MiniClaw 是一个轻量级 WeLink CLI AI 助理，支持文本对话、图片理解、工具调用和技能加载。

**核心目标**：用最小复杂度演示完整的 AI Agent 应用开发流程。

**实现方式**：单文件 `weblinkcli_agent.py`，所有模块集中在一个文件中，降低理解门槛。

---

## 架构设计

### 整体数据流

```
WeLink 群消息（文本/图片）
   │  welink-cli im query-history-message（轮询）
   ▼
get_recent_messages()  →  InboundMessage
   │
   ▼
build_prompt()  →  构造 Agent 输入（含图片下载）
   │
   ▼
Main Agent（CrewAI Agent）
   ├─ FileWriterTool / FileReadTool  （文件读写）
   ├─ AddImageTool                    （图片 → base64）
   └─ SkillLoaderTool                 （会议纪要 / 图片分析）
   │
   ▼
send_to_group()  →  welink-cli im send-to-group
   │
   ▼
WeLink 群
```

### 单文件内部模块划分

`weblinkcli_agent.py` 按以下顺序组织，每个区块用注释分隔线标注：

| 区块 | 核心类/函数 | 职责 |
|------|-----------|------|
| 配置 | `Config`, `config` | 从环境变量读取运行参数 |
| 消息模型 | `InboundMessage` | Pydantic 数据模型，解析 welink-cli 原始消息 |
| LLM | `LoggedLLM`, `create_llm()` | 带日志的 LLM 封装 |
| 工具：图片加载 | `AddImageTool` | 图片 → base64 data URI |
| 工具：技能加载器 | `SkillLoaderTool`, `SKILLS` | 动态创建 Sub-Crew 执行专业任务 |
| Agent | `create_main_agent()` | 组装 Agent + 工具 |
| WeLink CLI | `run_welink_command()`, `get_recent_messages()`, `download_image()`, `send_to_group()` | CLI 调用、消息拉取/发送 |
| 已回复追踪 | `RepliedTracker` | 持久化已回复 msg_id，避免重复回复 |
| 消息处理 | `handle_message()`, `build_prompt()` | Agent 调用与图片提示构造 |
| 主循环 | `main()` | 轮询 → 去重 → 处理 → 回复 |

---

## 核心模块详解

### 1. 配置（Config）

从根目录 `.env` 文件加载环境变量（由 IDE 运行配置注入），不依赖 `python-dotenv`。

```python
class Config:
    OPENAI_MODEL: str       # LLM 模型名
    OPENAI_API_KEY: str     # API 密钥
    OPENAI_API_BASE: str    # API 地址
    WELINK_GROUP_ID: str    # 监听群 ID
    CHECK_INTERVAL: int     # 轮询间隔（秒）
    RECENT_MINUTES: int     # 拉取最近 N 分钟消息
    WORKSPACE: Path         # 运行时工作目录
```

工作目录结构：`workspace/{group_id}/{images,files}`

### 2. 消息模型（InboundMessage）

```python
class InboundMessage(BaseModel):
    group_id: str             # 群 ID
    content: str              # 文本内容
    image_url: Optional[str]  # 图片 URL（如有）
    msg_id: str               # WeLink 消息 ID
    sender_name: str          # 发送者姓名
```

通过 `InboundMessage.from_raw(group_id, raw_dict)` 从 welink-cli 返回的 JSON 字典构造。

### 3. LLM 封装（LoggedLLM）

继承 `crewai.LLM`，在 `call()` 前后记录日志，提供调试可见性。

```python
class LoggedLLM(LLM):
    def call(self, *args, **kwargs) -> str:
        logger.info("LLM request: ...")
        result = super().call(*args, **kwargs)
        logger.info("LLM response: ...")
        return result
```

### 4. 工具

#### AddImageTool — 多模态图片加载

将本地图片转为 `data:image/<ext>;base64,<data>` URI，供多模态 LLM 理解图片内容。

使用场景：用户发送图片消息 → `build_prompt()` 下载图片到本地 → 提示 Agent 调用 `add_image` 加载。

#### SkillLoaderTool — 技能加载器

根据技能名动态创建 Sub-Crew（Agent + Task + Crew）执行专业任务。

预定义技能：

| 技能名 | 描述 | 输入 | 输出 |
|--------|------|------|------|
| `meeting_summary` | 整理会议纪要 | `raw_notes` | `attendees`, `key_decisions`, `action_items` |
| `image_analyzer` | 分析图片内容 | `image_path` | `description`, `key_elements`, `text_content` |

### 5. Main Agent

```python
def create_main_agent(llm) -> Agent:
    return Agent(
        role="WeLink 办公助手",
        tools=[FileWriterTool(), FileReadTool(), AddImageTool(), SkillLoaderTool(...)],
        llm=llm,
        verbose=True,
        multimodal=True,
    )
```

### 6. WeLink CLI 集成

| 函数 | 职责 |
|------|------|
| `run_welink_command(args)` | 调用 `welink-cli` 子进程 |
| `get_recent_messages(group_id, minutes)` | 拉取时间窗口内消息，按时间降序 |
| `download_image(url, path)` | 下载图片到本地 |
| `send_to_group(group_id, text)` | 发送回复（带 `【AI助手】` 前缀） |

### 7. 已回复追踪（RepliedTracker）

持久化已回复 msg_id 到 `workspace/{group_id}/replied_msgs.json`，重启后自动恢复。

### 8. 主循环

```
while True:
    messages = get_recent_messages(group_id, RECENT_MINUTES)
    latest = messages[0]

    if tracker.is_replied(latest.msg_id):  → 跳过
    if text < 2 字符 或 AI 自身回复:       → 跳过
    prompt = build_prompt(latest, images_dir)  → 含图片下载
    reply = handle_message(agent, prompt)      → Agent.kickoff()
    send_to_group(group_id, reply)
    tracker.mark_replied(latest.msg_id)

    time.sleep(CHECK_INTERVAL)
```

---

## 环境配置

根目录 `.env` 文件：

```env
# LLM 模型配置
OPENAI_MODEL=deepseek-v4-pro
OPENAI_API_KEY=sk-xxx
OPENAI_API_BASE=https://api.deepseek.com/v1

# WeLink 配置
WELINK_GROUP_ID=your-group-id-here
CHECK_INTERVAL=30
RECENT_MINUTES=30
```

---

## 项目结构

```
miniclaw_course/
├── .env                          # 环境变量（所有 test 共用）
├── pyproject.toml                # 项目依赖
├── test6/
│   ├── weblinkcli_agent.py       # CrewAI Agent 版本（单文件）
│   ├── welinkcli_llm.py          # 直接 LLM 调用版本（对比用）
│   ├── SPEC.md                   # 本文档
│   └── README.md                 # 开发指南
└── test1~5/                      # 前置学习模块
```

运行时自动生成：

```
test6/workspace/{group_id}/
├── images/          # 下载的图片
├── files/           # Agent 生成的文件
└── replied_msgs.json  # 已回复消息记录
```

---

## 依赖

`pyproject.toml` 中声明的直接依赖：

| 包 | 用途 |
|---|------|
| `crewai` | Agent 框架（Agent, Crew, LLM, Task） |
| `crewai-tools>=1.15.1` | 内置工具（FileReadTool, FileWriterTool） |
| `pydantic` | 数据模型（InboundMessage） |
| `requests` | HTTP 请求（图片下载） |

---

## 扩展指南

### 新增技能

在 `SKILLS` 列表中添加配置即可，Sub-Crew 会自动创建：

```python
SKILLS.append({
    "name": "new_skill",
    "description": "技能描述",
    "input_schema": {"field": "说明"},
    "output_schema": {"result": "说明"},
})
```

### 新增工具

继承 `BaseTool`，实现 `_run()` 方法，添加到 Agent 的 `tools` 列表。

---

## 常见问题

**Q: 轮询延迟大吗？**
默认 30 秒，延迟在 30 秒以内。可调小 `CHECK_INTERVAL`，但不要太小以免频繁请求。

**Q: CrewAI Agent vs 直接 call_llm？**
CrewAI Agent 支持工具调用、多步推理和技能加载。`welinkcli_llm.py` 是直接调用版本，可做对比。

**Q: 如何调试？**
`verbose=True` 查看 Agent 思考过程，`LoggedLLM` 查看 LLM 请求/响应日志。
