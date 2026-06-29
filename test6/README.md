# Test6 — 项目实战：使用 SPEC.md + 开发 Skill 完成 MiniClaw 开发

## 学习目标

通过 test6 掌握如何使用规范文档（SPEC.md）和业界开发 Skill（OpenSpec / SuperPowers）高效完成 AI Agent 项目开发。

---

## 核心概念

### 1. SPEC.md 的作用

SPEC.md 是项目的**技术蓝图**，定义了：
- 架构设计（模块划分、数据流）
- 核心接口（数据模型、函数签名）
- 实现细节（代码示例、配置说明）
- 学习路线（从简单到复杂）

**为什么需要 SPEC.md？**
- 让 AI 理解项目全貌，生成更准确的代码
- 让开发者快速上手，知道从哪里开始
- 让团队协作有统一的参考标准

### 2. 开发 Skill 的作用

开发 Skill 是**预配置的 AI 辅助工具**，帮助快速完成特定开发任务：

| Skill | 用途 | 适用场景 |
|-------|------|---------|
| **OpenSpec** | 从需求文档生成代码框架 | 项目初始化、模块搭建 |
| **SuperPowers** | 增强代码生成能力 | 复杂逻辑实现、优化重构 |
| **CodeReviewer** | 自动代码审查 | 提交前检查、质量保障 |
| **understand-anything** | 理解代码库 | 接手新项目、分析依赖 |

---

## 开发工作流

### 完整流程

```
1. 阅读 SPEC.md
   └─ 理解架构设计、模块划分、核心接口

2. 使用 OpenSpec 生成代码框架
   └─ 输入：SPEC.md 中的模块定义
   └─ 输出：目录结构、基础代码、接口定义

3. 使用 SuperPowers 实现核心逻辑
   └─ 输入：SPEC.md 中的实现细节
   └─ 输出：完整的业务逻辑代码

4. 使用 CodeReviewer 审查代码
   └─ 输入：生成的代码
   └─ 输出：优化建议、潜在问题

5. 使用 understand-anything 验证架构
   └─ 输入：完整项目
   └─ 输出：架构图、依赖关系、知识图谱
```

---

## 实战步骤

### Step 1: 阅读 SPEC.md

打开 `SPEC.md`，重点关注：

```markdown
## 架构设计
- 飞书集成层（listener.py / sender.py）
- Runner 执行引擎（runner.py）
- Main Agent（agents/main_agent.py）
- 多模态支持（tools/add_image_tool.py）
- Session 管理（session/manager.py）

## 核心模块
每个模块都有代码示例，可以直接复制使用
```

**学习目标**：理解消息从飞书接收到 Agent 处理再到回复的完整流程。

---

### Step 2: 使用 OpenSpec 生成代码框架

#### 方式 A：在 Claude Code 中使用

```bash
# 启动 Claude Code
claude

# 使用 OpenSpec Skill
/use-skill open-spec

# 输入提示
请根据 SPEC.md 生成 MiniClaw 项目的代码框架，包括：
1. 目录结构
2. 每个模块的基础代码（类定义、函数签名）
3. 必要的配置文件（pyproject.toml、.env.template）
```

#### 方式 B：手动使用 OpenSpec

```bash
# 安装 OpenSpec CLI
pip install openspec-cli

# 从 SPEC.md 生成代码框架
openspec generate --spec SPEC.md --output miniclaw/

# 生成的目录结构
miniclaw/
├── __init__.py
├── main.py
├── runner.py
├── feishu/
│   ├── __init__.py
│   ├── listener.py
│   ├── sender.py
│   └── models.py
├── agents/
│   ├── __init__.py
│   └── main_agent.py
├── tools/
│   ├── __init__.py
│   ├── add_image_tool.py
│   └── skill_loader_tool.py
└── session/
    ├── __init__.py
    └── manager.py
```

---

### Step 3: 使用 SuperPowers 实现核心逻辑

#### 示例 1：实现 FeishuListener

```bash
# 在 Claude Code 中
/use-skill superpowers

# 输入提示
请根据 SPEC.md 中的"飞书集成层"部分，实现 FeishuListener 类：
- 使用 lark-oapi SDK 连接飞书 WebSocket
- 监听 im.message.receive_v1 事件
- 解析消息内容为 InboundMessage
- 如果有图片附件，下载到 workspace
```

**SuperPowers 会生成**：
```python
import lark_oapi as lark
from lark_oapi.adapter.flask import *
from miniclaw.feishu.models import InboundMessage

class FeishuListener:
    def __init__(self, app_id: str, app_secret: str, runner: Runner):
        self.client = lark.Client.builder() \
            .app_id(app_id) \
            .app_secret(app_secret) \
            .build()
        self.runner = runner

    async def start(self):
        """启动 WebSocket 监听"""
        # SuperPowers 生成的完整实现
        ...
```

#### 示例 2：实现 AddImageTool

```bash
# 输入提示
请根据 SPEC.md 中的"多模态支持"部分，实现 AddImageTool：
- 继承 crewai.tools.BaseTool
- 将图片转为 base64 data URL
- 支持 PNG、JPG、WEBP 格式
```

**SuperPowers 会生成**：
```python
from crewai.tools import BaseTool
import base64
from pathlib import Path
from pydantic import PrivateAttr

class AddImageTool(BaseTool):
    name: str = "add_image"
    description: str = "加载图片到上下文，用于分析图片内容"
    _supported_formats: set = PrivateAttr(default={".png", ".jpg", ".jpeg", ".webp"})

    def _run(self, image_path: str) -> str:
        """将图片转为 base64 data URL"""
        path = Path(image_path)
        
        # 验证文件存在
        if not path.exists():
            return f"错误：图片不存在 {image_path}"
        
        # 验证格式
        if path.suffix.lower() not in self._supported_formats:
            return f"错误：不支持的图片格式 {path.suffix}"
        
        # 读取并编码
        with open(path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()
        
        # 返回 data URL
        mime_type = f"image/{path.suffix[1:]}"
        return f"data:{mime_type};base64,{image_data}"
```

---

### Step 4: 使用 CodeReviewer 审查代码

```bash
# 在 Claude Code 中
/use-skill code-review

# 输入提示
请审查 miniclaw/runner.py 的实现，重点检查：
1. 并发安全（asyncio.Queue 使用是否正确）
2. 资源泄漏（Worker 是否会正确退出）
3. 错误处理（异常是否被捕获）
4. 性能瓶颈（是否有不必要的等待）
```

**CodeReviewer 会输出**：
```markdown
## 代码审查报告

### 问题 1: Worker 退出条件不明确
**位置**: runner.py:45
**问题**: Worker 协程没有空闲超时退出机制，可能导致资源泄漏
**建议**: 添加 asyncio.wait_for 超时，空闲 5 分钟后退出

### 问题 2: 异常未捕获
**位置**: runner.py:52
**问题**: _process() 方法调用未用 try-except 包裹
**建议**: 捕获异常并记录日志，避免单个消息失败导致整个 Worker 退出

### 优化建议
1. 使用 asyncio.Semaphore 限制并发 Worker 数量
2. 添加 metrics 统计（消息处理延迟、队列长度）
```

---

### Step 5: 使用 understand-anything 验证架构

```bash
# 在 Claude Code 中
/use-skill understand-anything:understand

# 输入提示
请分析 miniclaw/ 项目，生成：
1. 模块依赖图
2. 数据流图（消息从接收到回复的完整路径）
3. 关键类和函数的知识图谱
```

**understand-anything 会输出**：
```
模块依赖图：
  main.py
    ├─> runner.py
    │     ├─> session/manager.py
    │     └─> agents/main_agent.py
    │           ├─> tools/add_image_tool.py
    │           └─> tools/skill_loader_tool.py
    └─> feishu/listener.py
          └─> feishu/sender.py

数据流：
  飞书 WebSocket
    → FeishuListener.on_message()
    → Runner.enqueue()
    → SessionManager.load()
    → MainAgent.execute()
    → FeishuSender.reply()
```

---

## 开发 Skill 对比

| Skill | 输入 | 输出 | 最佳使用时机 |
|-------|------|------|-------------|
| **OpenSpec** | SPEC.md | 代码框架 | 项目启动阶段 |
| **SuperPowers** | 需求描述 | 完整实现 | 核心逻辑开发 |
| **CodeReviewer** | 代码文件 | 审查报告 | 提交前检查 |
| **understand-anything** | 项目目录 | 知识图谱 | 接手新项目 |

---

## 实际开发示例：实现 Runner

### 1. 从 SPEC.md 提取需求

```markdown
## Runner 执行引擎

**设计**：per-routing_key 串行队列
- 同一用户/群的消息按顺序处理
- 不同用户/群并行处理

```python
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
```
```

### 2. 使用 SuperPowers 补全实现

```bash
/use-skill superpowers

# 输入提示
请根据 SPEC.md 中的 Runner 设计，补全完整实现：
1. 添加 Worker 空闲超时退出（5分钟）
2. 添加异常处理（消息处理失败不影响后续消息）
3. 添加日志记录（消息接收、处理完成、Worker 创建/退出）
4. 添加 graceful shutdown（等待所有 Worker 完成）
```

### 3. 生成的完整代码

```python
import asyncio
import logging
from collections import defaultdict
from typing import Dict, Optional
from miniclaw.feishu.models import InboundMessage

logger = logging.getLogger(__name__)

class Runner:
    def __init__(self, agent, session_manager, idle_timeout: int = 300):
        self.agent = agent
        self.session_manager = session_manager
        self.idle_timeout = idle_timeout
        self.queues: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self.workers: Dict[str, asyncio.Task] = {}
        self._shutdown = False

    async def enqueue(self, msg: InboundMessage):
        """消息入队"""
        logger.info(f"消息入队: routing_key={msg.routing_key}, message_id={msg.message_id}")
        await self.queues[msg.routing_key].put(msg)
        
        # 创建 Worker（如果不存在）
        if msg.routing_key not in self.workers:
            self.workers[msg.routing_key] = asyncio.create_task(
                self._worker(msg.routing_key)
            )
            logger.info(f"创建 Worker: routing_key={msg.routing_key}")

    async def _worker(self, routing_key: str):
        """Worker 协程"""
        queue = self.queues[routing_key]
        
        while not self._shutdown:
            try:
                # 等待消息（带超时）
                msg = await asyncio.wait_for(
                    queue.get(), 
                    timeout=self.idle_timeout
                )
                
                # 处理消息
                await self._process(routing_key, msg)
                
            except asyncio.TimeoutError:
                # 空闲超时，退出 Worker
                logger.info(f"Worker 空闲超时，退出: routing_key={routing_key}")
                break
            except Exception as e:
                # 异常处理：记录日志，继续处理下一条消息
                logger.error(f"消息处理失败: routing_key={routing_key}, error={e}")
                continue
        
        # 清理
        if routing_key in self.workers:
            del self.workers[routing_key]

    async def _process(self, routing_key: str, msg: InboundMessage):
        """处理单条消息"""
        logger.info(f"开始处理消息: message_id={msg.message_id}")
        
        # 加载会话历史
        history = self.session_manager.get_history(routing_key)
        
        # 调用 Agent
        response = await self.agent.execute(msg, history)
        
        # 保存会话
        self.session_manager.append(routing_key, "user", msg.content)
        self.session_manager.append(routing_key, "assistant", response)
        
        # 发送回复（由 FeishuSender 处理）
        logger.info(f"消息处理完成: message_id={msg.message_id}")

    async def shutdown(self):
        """优雅关闭"""
        logger.info("Runner 开始关闭...")
        self._shutdown = True
        
        # 等待所有 Worker 完成
        if self.workers:
            await asyncio.gather(*self.workers.values(), return_exceptions=True)
        
        logger.info("Runner 关闭完成")
```

### 4. 使用 CodeReviewer 审查

```bash
/use-skill code-review

# 输入提示
请审查上面生成的 Runner 实现，检查并发安全和资源管理
```

---

## 学习检查清单

- [ ] 理解 SPEC.md 的作用和结构
- [ ] 知道如何使用 OpenSpec 生成代码框架
- [ ] 知道如何使用 SuperPowers 实现核心逻辑
- [ ] 知道如何使用 CodeReviewer 审查代码
- [ ] 知道如何使用 understand-anything 验证架构
- [ ] 能够根据 SPEC.md 完成一个模块的开发

---

## 常见问题

**Q: OpenSpec 和 SuperPowers 有什么区别？**

OpenSpec 侧重**项目结构**（目录、文件、接口定义），SuperPowers 侧重**代码实现**（业务逻辑、算法、优化）。通常先用 OpenSpec 搭框架，再用 SuperPowers 填内容。

**Q: 这些 Skill 是免费的吗？**

大部分开发 Skill 需要订阅（如 Claude Pro、Cursor Pro）。Claude Code 内置的 Skill（如 code-review、understand-anything）需要 Claude Code 许可证。

**Q: 可以不用这些 Skill，手动开发吗？**

当然可以。SPEC.md 已经提供了完整的代码示例，可以直接复制使用。开发 Skill 只是加速工具，不是必须的。

**Q: 如何让 AI 更好地理解 SPEC.md？**

在提示中明确引用 SPEC.md 的具体章节，例如："请根据 SPEC.md 第 3.2 节的 FeishuListener 设计实现代码"。

**Q: 生成的代码可以直接用吗？**

需要人工审查和调整。开发 Skill 生成的代码是**起点**，不是终点。建议使用 CodeReviewer 检查，并根据实际需求优化。
