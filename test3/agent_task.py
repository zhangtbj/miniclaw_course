"""
Bug 报告生成器（三任务链式工作流）

演示如何使用 Task 的 expected_output + Pydantic 模型精确控制 Agent 的输出格式，
实现 Bug 报告 → 根因分析 → 修复方案 的链式任务流。

学习要点：
- Pydantic 模型：用 output_pydantic 保证每个 Task 输出结构化数据
- Task context：上游 Task 输出自动传递给下游 Task
- Process.sequential：任务按依赖关系顺序执行
- result.tasks_output：访问每个 Task 的独立输出
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from crewai import Agent, Task, Crew, Process
from pydantic import BaseModel, Field
from typing import List
from llm.llm import LoggedLLM


# ==============================================================================
# Pydantic 数据模型定义
# ==============================================================================

class BugReport(BaseModel):
    """标准 Bug 报告"""
    title: str = Field(..., description="Bug 标题，一句话概括问题")
    severity: str = Field(..., description="严重等级：P0 阻塞 / P1 严重 / P2 一般 / P3 轻微")
    severity_reason: str = Field(..., description="严重等级判断依据")
    reproduction_steps: List[str] = Field(..., description="复现步骤，每步一个具体操作")
    expected_behavior: str = Field(..., description="预期行为")
    actual_behavior: str = Field(..., description="实际行为")
    environment: str = Field(..., description="环境信息，如无法推断则写'待确认'")
    missing_info: List[str] = Field(default_factory=list, description="待补充信息列表")


class RootCauseItem(BaseModel):
    """单条根因分析"""
    name: str = Field(..., description="根因名称")
    layer: str = Field(..., description="技术层面：前端/后端/数据/网络/基础设施")
    likelihood: str = Field(..., description="可能性：高/中/低")
    reasoning: str = Field(..., description="判断依据")
    verification: str = Field(..., description="验证方法")


class RootCauseReport(BaseModel):
    """根因分析报告"""
    root_causes: List[RootCauseItem] = Field(..., description="所有可能的根因列表")
    most_likely: str = Field(..., description="最可能的 1-2 个根因及理由总结")


class FixOption(BaseModel):
    """单个修复方案"""
    name: str = Field(..., description="方案名称")
    implementation: List[str] = Field(..., description="技术实现步骤")
    estimated_effort: str = Field(..., description="预估工时（人天）")
    pros: List[str] = Field(..., description="优点列表")
    cons: List[str] = Field(..., description="缺点/风险列表")


class FixSuggestionReport(BaseModel):
    """修复方案对比报告"""
    options: List[FixOption] = Field(..., description="所有修复方案列表")
    recommendation: str = Field(..., description="推荐方案及理由")
    follow_up: List[str] = Field(..., description="后续建议，防止类似问题再次发生")


# ==============================================================================
# Agent 定义
# ==============================================================================

qa_expert = Agent(
    role='资深测试工程师',
    goal='将用户口头描述的问题转换为结构清晰、可复现的标准 Bug 报告',
    backstory="""
    你是一位拥有 10 年经验的 QA 专家，擅长从模糊的问题描述中提炼出关键信息。

    **你的能力**：
    - 能从"登录后偶尔白屏"这样的描述中推断出可能的复现路径
    - 会根据问题特征判断严重等级（P0-P3）
    - 会主动补充开发者排查问题所需的上下文信息

    **输出原则**：
    - 复现步骤必须具体到可操作（不要写"正常使用"，要写"点击XX按钮"）
    - 预期行为和实际行为要形成明确对比
    - 如果原始描述信息不足，在 missing_info 中标注

    **语言要求**：所有输出使用中文。
    """,
    llm=LoggedLLM(
        model=os.getenv("OPENAI_MODEL", "deepseek-v4-pro"),
    ),
    verbose=True,
    allow_delegation=False,
    output_pydantic=BugReport,
)

tech_lead = Agent(
    role='技术负责人',
    goal='基于 Bug 报告进行根因分析，并给出可行的修复方案',
    backstory="""
    你是一位拥有 12 年经验的技术负责人，主导过多个系统的故障排查和架构优化。

    **你的能力**：
    - 能从 Bug 现象反推可能的技术根因（前端/后端/网络/数据库/缓存等层面）
    - 会评估每个根因的可能性（高/中/低）并说明判断依据
    - 能给出多个修复方案并对比各自的优缺点和实施成本

    **工作原则**：
    - 根因分析要覆盖多个技术层面，不要只盯着一个方向
    - 修复方案要具体到技术实现（如"加 Redis 缓存"而非"优化性能"）
    - 每个方案要标注预估工时和风险评估

    **语言要求**：所有输出使用中文。
    """,
    llm=LoggedLLM(
        model=os.getenv("OPENAI_MODEL", "deepseek-v4-pro"),
    ),
    verbose=True,
    allow_delegation=False,
    output_pydantic=FixSuggestionReport,
)


# ==============================================================================
# Task 定义
# ==============================================================================

bug_report_task = Task(
    description="""
    根据以下用户反馈，生成一份标准 Bug 报告：

    {bug_description}

    报告必须包含：标题、严重等级（含判断依据）、复现步骤、预期行为、实际行为、环境信息、待补充信息。
    """,
    expected_output="一个完整的 BugReport 结构化输出。",
    agent=qa_expert,
    output_pydantic=BugReport,
)

root_cause_task = Task(
    description="""
    基于上游 Bug 报告，从多个技术层面分析可能的根因。

    分析维度：
    - 前端/客户端层（渲染、状态管理、内存泄漏）
    - 后端服务层（接口超时、异常处理、并发问题）
    - 数据层（数据库慢查询、缓存穿透、数据不一致）
    - 网络层（DNS、CDN、连接池）
    - 基础设施层（资源瓶颈、配置错误）

    每个根因需要标注可能性等级（高/中/低）、判断依据和验证方法。
    """,
    expected_output="一个完整的 RootCauseReport 结构化输出。",
    agent=tech_lead,
    output_pydantic=RootCauseReport,
    context=[bug_report_task],
)

fix_suggestion_task = Task(
    description="""
    基于上游 Bug 报告和根因分析，给出具体的修复方案。

    要求：
    - 给出 2-3 个修复方案，每个方案具体到技术实现
    - 对比各方案的优缺点、实施成本和风险
    - 给出推荐方案及理由
    - 给出后续建议，防止类似问题再次发生
    """,
    expected_output="一个完整的 FixSuggestionReport 结构化输出。",
    agent=tech_lead,
    output_pydantic=FixSuggestionReport,
    context=[bug_report_task, root_cause_task],
)


# ==============================================================================
# Crew 执行
# ==============================================================================

# 模拟一段口头 Bug 描述
bug_input = """
用户反馈：用华为 Mate80 打开我们的商城 App，登录后点"我的订单"，
有时候会闪退，不是每次都发生，大概是用了十几分钟之后比较容易出问题。
其他页面好像没问题。
"""

crew = Crew(
    agents=[qa_expert, tech_lead],
    tasks=[bug_report_task, root_cause_task, fix_suggestion_task],
    process=Process.sequential,
    verbose=True,
)

result = crew.kickoff(inputs={"bug_description": bug_input})

# ==============================================================================
# 输出结果
# ==============================================================================

print("\n" + "=" * 80)
print("Crew 执行完成！")
print("=" * 80)

# 打印最终结构化输出
print("\n最终输出（原始文本）:")
print(result.raw)

# 访问结构化数据
if result.pydantic:
    print("\n" + "=" * 80)
    print("最终输出（结构化数据）:")
    print("=" * 80)
    final = result.pydantic
    print(f"\n【推荐方案】{final.recommendation}")
    for i, opt in enumerate(final.options, 1):
        print(f"\n  方案{i}：{opt.name}（{opt.estimated_effort}）")
        print(f"    优点：{', '.join(opt.pros)}")
        print(f"    风险：{', '.join(opt.cons)}")

# 访问每个任务的输出
print("\n" + "=" * 80)
print("所有任务的输出:")
print("=" * 80)
for i, task_output in enumerate(result.tasks_output, 1):
    print(f"\n任务 {i}: {task_output.description[:50]}...")
    if task_output.pydantic:
        print(f"  输出类型: {type(task_output.pydantic).__name__}")
    print(f"  原始输出长度: {len(task_output.raw)} 字符")
