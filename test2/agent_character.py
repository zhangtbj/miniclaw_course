"""
演示如何使用 Agent.kickoff() 直接与 Agent 交互，从多维度评审技术方案。
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from crewai import Agent
from llm.llm import LoggedLLM
from tools.intermediate_tool import IntermediateTool


# ==============================================================================
# Agent 定义
# ==============================================================================

tech_reviewer = Agent(
    role='资深技术评审专家',
    goal='从架构、安全、性能、可维护性四个维度对技术方案进行系统性评审，给出具体改进建议。',
    backstory="""
    你是一位拥有 15 年经验的资深架构师，曾多次主导大型系统的技术评审。

    **评审维度**：
    1. 架构合理性：模块划分是否清晰、耦合度是否可控、是否过度设计或设计不足
    2. 安全性：认证鉴权是否完善、数据是否加密、是否存在注入/越权风险
    3. 性能：是否存在瓶颈、是否有 N+1 查询、缓存策略是否合理
    4. 可维护性：代码可读性、日志与监控是否完备、是否有清晰的降级方案

    **工作原则**：
    - 先理解方案的业务背景和目标，再展开评审
    - 每个问题要说明"为什么是问题"和"建议怎么改"
    - 按严重程度分级：🔴 阻塞性 / 🟡 建议优化 / 🟢 锦上添花
    - 使用 IntermediateTool 分步骤记录每个维度的分析结论

    **语言要求**：所有输出使用中文。
    """,
    verbose=True,
    allow_delegation=False,
    tools=[IntermediateTool()],
    llm=LoggedLLM(
        model=os.getenv("OPENAI_MODEL", "deepseek-v4-pro"),
    ),
)


# ==============================================================================
# 执行任务
# ==============================================================================

# 模拟一份待评审的技术方案摘要
proposal = """
## 技术方案：用户积分系统

### 背景
为支撑运营活动，需要建设用户积分系统，支持积分的获取、消耗和查询。

### 方案概述
- 使用 MySQL 单库存储积分流水和余额
- 提供 RESTful API：POST /earn, POST /spend, GET /balance
- 定时任务每天凌晨统计用户等级
- 无缓存，直接查库
- 接口通过 API Key 鉴权
"""

messages = [
    {
        "role": "user",
        "content": f"请对以下技术方案进行评审：\n{proposal}"
    }
]

result = tech_reviewer.kickoff(messages)
print(result)
