# Test6 — 使用开发 Skill 完成 MiniClaw 开发

## 学习目标

掌握如何使用 OpenSpec、Superpowers、Code Review 三个开发 Skill 串联完成 AI Agent 项目开发。

---

## 开发工作流

```
1. OpenSpec        →  从需求描述生成技术规格（SPEC）
2. Superpowers     →  brainstorming + 代码实现
3. Code Review     →  审查代码质量与潜在问题
```

---

## Step 1: 使用 OpenSpec 生成需求规格

### 目的

将模糊的产品需求转化为结构化的技术规格文档，包含架构设计、模块划分、核心接口定义。

### 操作

在 Claude Code 中使用 `/openspec` skill（或通过 `.opencode/skills/openspec/` 安装），输入项目需求：

```
请根据以下需求生成技术规格：

项目名称：MiniClaw WeLink CLI AI 助理
核心需求：
- 监听 WeLink 群消息（文本和图片）
- 使用 CrewAI Agent 处理消息并生成回复
- 支持多模态（图片理解）
- 支持技能扩展（会议纪要、图片分析）
- 通过 welink-cli 收发消息
```

### OpenSpec 输出

OpenSpec 会生成结构化的技术规格，包含：

- **架构设计**：数据流图、模块划分
- **核心接口**：InboundMessage 模型、Config 配置类、函数签名
- **模块职责**：每个区块的输入/输出/职责定义
- **配置说明**：环境变量、依赖清单

> 生成的规格内容可参考本目录下的 `SPEC.md`，作为后续开发的蓝图。

---

## Step 2: 使用 Superpowers 进行 Brainstorming 和开发

### 2.1 Brainstorming — 设计讨论

在编码前，使用 Superpowers 的 brainstorming 能力讨论设计决策：

```
请使用 brainstorming 帮我讨论以下设计决策：

1. 单文件 vs 多文件：
   - 教学项目，单文件降低理解门槛
   - 用注释分隔线组织模块

2. 消息去重策略：
   - 持久化 JSON vs 内存 set
   - 需要支持重启恢复

3. 图片处理流程：
   - 先下载到本地再 base64 编码
   - vs 直接内存中转

4. 技能扩展方式：
   - 配置驱动 vs 代码驱动
   - Sub-Crew 动态创建
```

Superpowers 会从多个角度分析 tradeoff，帮助做出合理的设计决策。

### 2.2 代码实现

确定设计后，使用 Superpowers 逐步实现：

```
请根据技术规格实现 weblinkcli_agent.py，单文件包含所有模块：

1. Config 类 — 从 os.getenv 读取配置
2. InboundMessage — Pydantic 模型，from_raw 类方法
3. LoggedLLM — 继承 crewai.LLM，记录日志
4. AddImageTool — 图片转 base64 data URI
5. SkillLoaderTool — 动态创建 Sub-Crew
6. create_main_agent — 组装 Agent + 工具
7. WeLink CLI 函数 — subprocess 调用 welink-cli
8. RepliedTracker — JSON 持久化去重
9. main() — 轮询主循环
```

Superpowers 会生成完整的实现代码，包含错误处理、日志记录和类型注解。

---

## Step 3: 使用 Code Review 审查代码

### 目的

在提交前检查代码质量，发现潜在问题和改进点。

### 操作

使用 `/code-review` skill 对代码进行审查：

```
/code-review
```

### 审查维度

Code Review 会检查以下方面：

| 维度 | 检查内容 |
|------|---------|
| **正确性** | subprocess 超时处理、JSON 解析异常、去重逻辑 |
| **安全性** | API Key 不硬编码、subprocess 参数注入防护 |
| **健壮性** | 网络请求超时、文件 IO 异常、LLM 调用失败 |
| **性能** | 轮询间隔合理性、图片大小限制、内存占用 |
| **可维护性** | 模块组织、类型注解、文档字符串 |

### 根据审查结果修复

```
请根据 code-review 的发现修复问题，重点关注：
1. 异常处理是否完善
2. 资源是否正确释放
3. 边界条件是否覆盖
```

---

## 快速开始

### 前置条件

```bash
# 安装依赖
uv sync

# 确保 welink-cli 可用
welink-cli --version

# 配置根目录 .env（参考项目根目录的 .env 模板）
```

### 运行

```bash
uv run python test6/weblinkcli_agent.py
```

### 测试

在 WeLink 群中发送：
- 文本消息："帮我整理一下会议纪要"
- 图片 + 文字：发送截图 + "帮我看看这个报错"

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `weblinkcli_agent.py` | CrewAI Agent 版本（单文件，主版本） |
| `welinkcli_llm.py` | 直接 LLM 调用版本（对比参考） |
| `SPEC.md` | 技术规格文档 |
| `README.md` | 本文档 |

---

## 学习检查清单

- [ ] 理解 OpenSpec 如何将需求转化为技术规格
- [ ] 理解 Superpowers brainstorming 如何辅助设计决策
- [ ] 理解 Code Review 的检查维度和修复流程
- [ ] 能够独立使用三个 Skill 完成一个新模块的开发
