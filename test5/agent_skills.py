"""
Skills 生态简化示例：办公小助手

演示 SkillLoaderTool 如何让 Agent 按需加载技能：
- 3 个办公技能：会议纪要、邮件撰写、任务提取
- Agent 根据用户需求自动选择合适的技能
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

load_dotenv(project_root / ".env")

from crewai import Agent, Task, Crew
from llm.llm import LoggedLLM
from tools.skill_loader_tool import SkillLoaderTool


# ==============================================================================
# 定义办公技能（Skill）
# ==============================================================================

SKILLS = [
    {
        "name": "meeting_summary",
        "type": "task",
        "description": "将杂乱的会议记录整理为结构化纪要",
        "input_schema": {
            "raw_notes": "原始会议记录文本"
        },
        "output_schema": {
            "attendees": "参会人列表",
            "key_decisions": "关键决策",
            "action_items": "待办事项"
        }
    },
    {
        "name": "email_drafter",
        "type": "task",
        "description": "根据要点生成专业的商务邮件",
        "input_schema": {
            "recipient": "收件人",
            "purpose": "邮件目的",
            "key_points": "核心要点列表"
        },
        "output_schema": {
            "subject": "邮件主题",
            "body": "邮件正文"
        }
    },
    {
        "name": "task_extractor",
        "type": "task",
        "description": "从文本中提取待办任务",
        "input_schema": {
            "text": "源文本"
        },
        "output_schema": {
            "tasks": [{"owner": "负责人", "task": "任务描述", "deadline": "截止时间"}]
        }
    }
]


# ==============================================================================
# Agent 定义
# ==============================================================================

office_assistant = Agent(
    role="办公小助手",
    goal="根据用户需求，调用合适的办公技能完成任务",
    backstory="""
    你是一位高效的办公助手，擅长使用各种技能工具帮助员工处理日常工作。

    工作流程：
    1. 理解用户需求
    2. 使用 skill_loader 加载合适的技能
    3. 调用技能完成任务
    4. 返回结果给用户

    可用技能类型：
    - meeting_summary：整理会议纪要
    - email_drafter：撰写商务邮件
    - task_extractor：提取待办任务
    """,
    tools=[SkillLoaderTool(
        skills=SKILLS,
        llm=LoggedLLM(model=os.getenv("OPENAI_MODEL", "deepseek-v4-pro"))
    )],
    llm=LoggedLLM(
        model=os.getenv("OPENAI_MODEL", "deepseek-v4-pro"),
    ),
    verbose=True,
)


# ==============================================================================
# 演示场景
# ==============================================================================

def demo_meeting():
    """场景1：整理会议纪要"""
    print("=" * 60)
    print("场景1：整理会议纪要")
    print("=" * 60)

    task = Task(
        description="帮我整理这份会议记录：{notes}",
        expected_output="结构化的会议纪要",
        agent=office_assistant,
    )

    crew = Crew(agents=[office_assistant], tasks=[task])

    notes = """
    今天下午3点开了产品评审会，参会的有产品张三、开发李四、设计王五。
    讨论了新版本的功能，决定先上线用户反馈最多的深色模式。
    李四说开发需要两周，王五负责出设计稿，下周一前交付。
    张三要整理用户测试计划，也是下周完成。
    """

    result = crew.kickoff(inputs={"notes": notes})
    print(f"\n结果：\n{result}\n")


def demo_email():
    """场景2：撰写商务邮件"""
    print("=" * 60)
    print("场景2：撰写商务邮件")
    print("=" * 60)

    task = Task(
        description="帮我写一封邮件：{email_request}",
        expected_output="完整的邮件（主题+正文）",
        agent=office_assistant,
    )

    crew = Crew(agents=[office_assistant], tasks=[task])

    request = """
    发给客户张总，目的是通知项目延期。
    要点：1）原定下周交付改为下月15号 2）原因是需求变更 3）保证质量不变
    """

    result = crew.kickoff(inputs={"email_request": request})
    print(f"\n结果：\n{result}\n")


if __name__ == "__main__":
    print("\n办公小助手 Skills 演示\n")

    # 运行两个场景
    demo_meeting()
    demo_email()
