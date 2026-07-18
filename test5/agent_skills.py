"""
Skills 生态简化示例：办公小助手

演示 SkillLoaderTool 如何让 Agent 按需加载技能：
- 3 个办公技能：会议纪要、邮件撰写、任务提取
- Agent 根据用户需求自动选择合适的技能
"""

import sys
import os
import re
from pathlib import Path
import yaml
from dotenv import load_dotenv

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

load_dotenv(project_root / ".env")

from crewai import Agent, Task, Crew
from llm.llm import LoggedLLM
from tools.skill_loader_tool import SkillLoaderTool


# ==============================================================================
# 从 skills/ 目录加载技能（每个技能是一个 SKILL.md 文件）
# ==============================================================================
# 目录约定：skills/<skill_name>/SKILL.md
# SKILL.md 沿用标准 skill 格式：frontmatter 只声明 name / description，
# 正文写操作指引（处理步骤 + 输出要求）。
# 这比把技能写死在数组里更接近真实 skill 生态：新增技能只要加一个目录。


def load_skills(skills_dir: Path) -> list[dict]:
    """读取 skills_dir 下每个子目录的 SKILL.md，解析为技能配置列表。"""
    skills: list[dict] = []
    for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
        text = skill_file.read_text(encoding="utf-8")

        # 拆分 YAML frontmatter 与 markdown 正文
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
        if not match:
            raise ValueError(f"{skill_file} 缺少 YAML frontmatter（--- ... ---）")

        meta = yaml.safe_load(match.group(1))
        body = match.group(2).strip()

        skills.append({
            "name": meta["name"],
            "description": meta["description"],
            "instructions": body,
        })

    return skills


SKILLS_DIR = Path(__file__).parent / "skills"
SKILLS = load_skills(SKILLS_DIR)


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
