"""
笔记助手 — Agent 使用工具读写文件

演示 Agent 如何使用 CrewAI 内置工具（FileWriterTool / FileReadTool）操作文件：
1. Agent 自主决定何时读文件、何时写文件
2. 多轮对话通过文件持久化状态

学习要点：
- 工具调用：Agent 能操作外部世界（不只是生成文本）
- 工具选择：Agent 根据任务自动选择合适的工具
"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from crewai import Agent, Task, Crew
from crewai_tools import FileWriterTool, FileReadTool
from llm.llm import LoggedLLM


# ==============================================================================
# Agent 定义
# ==============================================================================

note_agent = Agent(
    role="笔记助手",
    goal="帮用户记录和查询笔记",
    backstory="""
    你是一个简单的笔记助手。用户让你记东西，你就写入 notes.md；
    用户让你查东西，你就读取 notes.md。每条笔记一行，格式："- 内容"。
    """,
    tools=[FileWriterTool(), FileReadTool()],
    llm=LoggedLLM(
        model=os.getenv("OPENAI_MODEL", "deepseek-v4-pro"),
    ),
    verbose=True,
)


# ==============================================================================
# Task 和 Crew
# ==============================================================================

task = Task(
    description="{user_input}",
    expected_output="对用户的简短回复",
    agent=note_agent,
)

crew = Crew(agents=[note_agent], tasks=[task], verbose=True)


# ==============================================================================
# 两轮对话
# ==============================================================================

# 第一轮：写笔记
print("=" * 60)
print("第一轮：记笔记")
print("=" * 60)
result = crew.kickoff(inputs={"user_input": "帮我记三条：1）明天下午3点开会 2）周五前提交代码 3）下周review技术方案"})
print(f"\n结果：{result}\n")

# 第二轮：查笔记
print("=" * 60)
print("第二轮：查笔记")
print("=" * 60)
result = crew.kickoff(inputs={"user_input": "我记了哪些事情？"})
print(f"\n结果：{result}\n")
