"""
简化版 SkillLoaderTool：动态加载和执行技能

演示 Skills 生态的核心概念：
- Agent 持有一个"技能加载器"工具
- 根据需求动态创建 Sub-Crew 执行具体技能
- 每个技能是一个独立的小 Crew
"""

from crewai.tools import BaseTool
from crewai import Agent, Task, Crew
from pydantic import PrivateAttr

# 注：标准 skill 的输出格式写在 SKILL.md 正文里，不再有 output_schema，
# 因此 expected_output 改为引用技能描述。


class SkillLoaderTool(BaseTool):
    name: str = "skill_loader"
    description: str = "加载并执行指定的办公技能"

    _skills: list = PrivateAttr(default_factory=list)
    _llm: object = PrivateAttr(default=None)

    def __init__(self, skills: list, llm=None, **kwargs):
        super().__init__(**kwargs)
        self._skills = skills
        self._llm = llm

        # 构建技能描述
        skills_desc = "\n".join([
            f"- {s['name']}: {s['description']}"
            for s in skills
        ])
        self.description = (
            f"加载并执行指定的办公技能。\n"
            f"可用技能：\n{skills_desc}\n\n"
            f"使用方法：传入 skill_name 和 skill_input"
        )

    def _run(self, skill_name: str, skill_input: str) -> str:
        """执行指定技能"""
        # 查找技能定义
        skill_def = next((s for s in self._skills if s['name'] == skill_name), None)
        if not skill_def:
            return f"错误：未找到技能 '{skill_name}'"

        print(f"\n🔧 加载技能：{skill_name}")
        print(f"   输入：{skill_input[:100]}...")

        # 创建执行该技能的 Sub-Crew
        skill_agent = Agent(
            role=f"{skill_name} 专家",
            goal=f"执行 {skill_def['description']}",
            backstory=f"你是 {skill_def['description']} 的专家。",
            verbose=False,
            llm=self._llm,  # 使用主 Agent 的 LLM
        )

        # SKILL.md 的正文（instructions）作为操作指引注入子 Agent；
        # 没有 instructions 的旧配置仍能正常工作（向后兼容）。
        instructions = skill_def.get("instructions")
        task_desc = ""
        if instructions:
            task_desc += f"请按以下操作指引执行：\n{instructions}\n\n"
        task_desc += f"任务输入：\n{skill_input}"

        skill_task = Task(
            description=task_desc,
            expected_output=f"按操作指引完成任务：{skill_def['description']}",
            agent=skill_agent,
        )

        skill_crew = Crew(
            agents=[skill_agent],
            tasks=[skill_task],
            verbose=False,
        )

        # 执行技能
        result = skill_crew.kickoff()
        print(f"   ✅ 技能执行完成")

        return str(result)
