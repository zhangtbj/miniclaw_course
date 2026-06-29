# MiniClaw 飞书 AI 助理 — 技术规范

## 项目概述

MiniClaw 是一个轻量级飞书 AI 助理，集成 test1-5 的核心能力，支持文本对话、图片理解、工具调用和技能加载。

**核心目标**：用最小复杂度演示完整的 AI Agent 应用开发流程。

---

## 架构设计

### 整体架构

```
飞书消息（文本/图片）
   │  WebSocket
   ▼
FeishuListener（消息接收）
   │  解析 → InboundMessage
   ▼
Runner（串行队列）
   │
   ├─ SessionManager（对话历史）
   │
   ▼
Main Agent（办公助手）
   │
   ├─ 工具：FileWriterTool / FileReadTool
   ├─ 技能：SkillLoaderTool
   │      ├─ meeting_summary（会议纪要）
   │      └─ image_analyzer（图片分析）
   │
   └─ 多模态：直接理解用户发送的图片
   │
   ▼
FeishuSender（回复消息）
```

### 与 XiaoPaw 的对比

| 特性 | XiaoPaw | MiniClaw |
|------|---------|----------|
| Skills 数量 | 9 个 | 2 个 |
| Sub-Crew 架构 | MCP Sandbox | 直接执行 |
| 凭证隔离 | .config 文件 | 环境变量 |
| 定时任务 | CronService | 无 |
| 会话管理 | JSONL + 原子写入 | 内存 + JSON |
| 复杂度 | 生产级 | 教学级 |

---

## 核心模块

### 1. 飞书集成层

**文件结构**：
```
miniclaw/
├── feishu/
│   ├── listener.py      # WebSocket 监听
│   ├── sender.py        # 消息发送
│   └── models.py        # InboundMessage
```

**InboundMessage 模型**：
```python
from pydantic import BaseModel
from typing import Optional

class InboundMessage(BaseModel):
    routing_key: str          # 用户ID 或 群ID
    content: str              # 文本内容
    image_url: Optional[str]  # 图片URL（如有）
    message_id: str           # 飞书消息ID
```

**消息处理流程**：
1. FeishuListener 接收 WebSocket 事件
2. 解析为 InboundMessage
3. 如果有图片，下载到本地
4. 传递给 Runner

---

### 2. Runner 执行引擎

**文件**：`miniclaw/runner.py`

**设计**：per-routing_key 串行队列
- 同一用户/群的消息按顺序处理
- 不同用户/群并行处理

```python
import asyncio
from collections import defaultdict

class Runner:
    def __init__(self):
        self.queues = defaultdict(asyncio.Queue)
        self.workers = {}

    async def enqueue(self, msg: InboundMessage):
        """消息入队"""
        await self.queues[msg.routing_key].put(msg)
        if msg.routing_key not in self.workers:
            self.workers[msg.routing_key] = asyncio.create_task(
                self._worker(msg.routing_key)
            )

    async def _worker(self, routing_key: str):
        """Worker 协程"""
        while True:
            msg = await self.queues[routing_key].get()
            await self._process(msg)
            # 空闲超时退出（省略）
```

---

### 3. Main Agent

**文件**：`miniclaw/agents/main_agent.py`

**核心设计**：
- 单 Agent + 多工具 + 技能加载器
- 支持多模态（图片理解）
- 集成 test1-5 的所有能力

```python
from crewai import Agent
from crewai_tools import FileWriterTool, FileReadTool
from tools.skill_loader_tool import SkillLoaderTool
from tools.add_image_tool import AddImageTool
from llm.llm import LoggedLLM

# 技能配置
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
    {
        "name": "image_analyzer",
        "type": "task",
        "description": "分析图片内容，提取关键信息",
        "input_schema": {"image_path": "图片文件路径"},
        "output_schema": {
            "description": "图片描述",
            "key_elements": "关键元素列表",
            "text_content": "图中的文字（如有）"
        }
    }
]

def create_main_agent(llm: LoggedLLM) -> Agent:
    """创建主 Agent"""
    return Agent(
        role="飞书办公助手",
        goal="帮助用户处理日常办公事务，支持文本对话和图片理解",
        backstory="""
        你是一位高效的飞书办公助手，擅长：
        1. 理解和回答用户的问题
        2. 分析用户发送的图片（如截图、文档照片）
        3. 使用工具读写文件
        4. 调用专业技能处理复杂任务（如整理会议纪要）

        工作流程：
        - 如果用户发送了图片，先分析图片内容
        - 根据用户需求选择合适的工具或技能
        - 返回清晰、结构化的结果
        """,
        tools=[
            FileWriterTool(),
            FileReadTool(),
            AddImageTool(),  # 多模态：加载图片
            SkillLoaderTool(skills=SKILLS, llm=llm)
        ],
        llm=llm,
        verbose=True,
    )
```

---

### 4. 多模态支持

**工具**：`miniclaw/tools/add_image_tool.py`

```python
from crewai.tools import BaseTool
import base64
from pathlib import Path

class AddImageTool(BaseTool):
    name: str = "add_image"
    description: str = "加载图片到上下文，用于分析图片内容"

    def _run(self, image_path: str) -> str:
        """将图片转为 base64"""
        path = Path(image_path)
        if not path.exists():
            return f"错误：图片不存在 {image_path}"

        with open(path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()

        return f"data:image/{path.suffix[1:]};base64,{image_data}"
```

**使用场景**：
1. 用户发送图片消息
2. FeishuListener 下载图片到 `workspace/{routing_key}/images/`
3. Agent 调用 `add_image` 工具加载图片
4. LLM 直接理解图片内容（多模态能力）

---

### 5. Session 管理

**文件**：`miniclaw/session/manager.py`

**简化设计**：内存 + JSON 持久化

```python
import json
from pathlib import Path
from typing import Dict, List

class SessionManager:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.sessions: Dict[str, List[dict]] = {}
        self._load()

    def append(self, routing_key: str, role: str, content: str):
        """追加消息到会话历史"""
        if routing_key not in self.sessions:
            self.sessions[routing_key] = []
        self.sessions[routing_key].append({"role": role, "content": content})
        self._save()

    def get_history(self, routing_key: str, max_turns: int = 10) -> List[dict]:
        """获取最近 N 轮对话"""
        history = self.sessions.get(routing_key, [])
        return history[-max_turns * 2:]  # 每轮包含 user + assistant

    def _save(self):
        """持久化到 JSON"""
        path = self.workspace / "sessions.json"
        with open(path, "w") as f:
            json.dump(self.sessions, f, ensure_ascii=False, indent=2)

    def _load(self):
        """从 JSON 加载"""
        path = self.workspace / "sessions.json"
        if path.exists():
            with open(path) as f:
                self.sessions = json.load(f)
```

---

### 6. 技能扩展

**image_analyzer 技能**：

```python
# 在 SKILLS 配置中已定义
# Sub-Crew 会自动创建并执行

# 示例调用流程：
# 1. 用户发送截图："帮我看看这个报错"
# 2. Agent 调用 add_image 工具加载图片
# 3. Agent 调用 skill_loader(skill_name="image_analyzer", ...)
# 4. Sub-Crew 分析图片，返回结构化结果
# 5. Agent 根据分析结果给出解答
```

---

## 使用业界开发 Skill

### 什么是开发 Skill？

开发 Skill 是预配置的 AI 辅助开发工具，帮助快速完成特定开发任务。常见的有：

- **OpenSpec**：从需求文档生成代码框架
- **SuperPowers**：增强代码生成能力
- **CodeReviewer**：自动代码审查

### 如何在 MiniClaw 中使用

#### 方式1：作为 CrewAI Skill

将开发 Skill 包装为 CrewAI Skill：

```python
SKILLS = [
    # ... 原有技能
    {
        "name": "code_generator",
        "type": "task",
        "description": "根据需求描述生成 Python 代码",
        "input_schema": {
            "requirement": "需求描述",
            "language": "编程语言（默认 Python）"
        },
        "output_schema": {
            "code": "生成的代码",
            "explanation": "代码说明"
        }
    }
]
```

#### 方式2：作为独立工具

```python
from tools.openai_spec_tool import OpenSpecTool

agent = Agent(
    tools=[
        # ... 其他工具
        OpenSpecTool()  # 直接集成
    ]
)
```

#### 方式3：Claude Code Skill

如果使用 Claude Code 开发，可以直接使用内置 Skill：

```bash
# 在 Claude Code 中
/use-skill understand-anything:understand  # 理解代码库
/use-skill code-review                      # 代码审查
/use-skill simplify                         # 简化代码
```

### 推荐工作流

```
1. 需求分析
   └─ 使用 OpenSpec 从需求文档生成技术方案

2. 代码开发
   └─ 使用 SuperPowers 增强代码生成
   └─ 使用 test1-5 的代码片段管理器保存常用代码

3. 代码审查
   └─ 使用 CodeReviewer 自动审查
   └─ 使用 test3 的技术方案评审助手

4. 测试验证
   └─ 使用 test4 的工具调用能力编写测试脚本

5. 部署上线
   └─ 使用飞书 Skills 发送部署通知
```

---

## 快速开始

### 1. 安装依赖

```bash
uv sync
```

### 2. 配置环境变量

```env
# .env
OPENAI_MODEL=deepseek-v4-pro
OPENAI_API_KEY=sk-xxx
OPENAI_API_BASE=https://api.deepseek.com/v1

FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
```

### 3. 飞书应用配置

1. 在飞书开放平台创建应用
2. 启用"机器人"能力
3. 添加事件订阅：`im.message.receive_v1`
4. 选择 WebSocket 模式（无需公网 IP）

### 4. 启动服务

```bash
uv run python -m miniclaw
```

### 5. 测试

在飞书中发送消息：
- 文本："帮我整理一下会议纪要"
- 图片：发送截图 + "帮我看看这个报错"
- 文件：发送会议记录文本

---

## 项目结构

```
miniclaw/
├── __init__.py
├── main.py                # 入口
├── runner.py              # 执行引擎
├── feishu/
│   ├── listener.py        # WebSocket 监听
│   ├── sender.py          # 消息发送
│   └── models.py          # 数据模型
├── agents/
│   └── main_agent.py      # 主 Agent
├── tools/
│   ├── add_image_tool.py  # 多模态工具
│   └── skill_loader_tool.py
├── session/
│   └── manager.py         # 会话管理
└── workspace/             # 运行时工作空间
    └── {routing_key}/
        ├── images/        # 下载的图片
        └── files/         # 生成的文件
```

---

## 扩展指南

### 新增技能

1. 在 `SKILLS` 列表中添加配置
2. 定义 input_schema 和 output_schema
3. Sub-Crew 会自动创建

### 新增工具

1. 继承 `crewai.tools.BaseTool`
2. 实现 `_run()` 方法
3. 添加到 Agent 的 tools 列表

### 支持更多消息类型

1. 扩展 `InboundMessage` 模型
2. 在 `FeishuListener` 中解析新事件类型
3. 在 Agent 的 backstory 中说明如何处理

---

## 学习路线

1. **阅读 test1-5**：理解 CrewAI 核心概念
2. **阅读 feishu/listener.py**：理解消息接收
3. **阅读 runner.py**：理解并发模型
4. **阅读 agents/main_agent.py**：理解 Agent 配置
5. **阅读 tools/add_image_tool.py**：理解多模态
6. **本地测试**：使用测试消息验证流程
7. **飞书集成**：配置真实飞书环境

---

## 常见问题

**Q: 为什么不使用 MCP Sandbox？**

MiniClaw 定位为教学项目，直接执行更简单易懂。生产环境建议使用 Sandbox 隔离代码执行。

**Q: 如何处理大图片？**

在 `FeishuListener` 中压缩图片，或在 `AddImageTool` 中限制大小。

**Q: 如何支持多轮对话？**

`SessionManager` 保存对话历史，Agent 的 prompt 中包含最近 N 轮历史。

**Q: 如何调试？**

设置 `verbose=True` 查看 Agent 思考过程，使用 `LoggedLLM` 查看 LLM 请求。
