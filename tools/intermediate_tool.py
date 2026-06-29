"""
IntermediateTool - Agent 中间结果保存工具

让 Agent 在多步推理过程中保存阶段性结论，避免遗忘，
最终输出时可以参考这些中间结果组织最终答案。
"""
from crewai.tools import BaseTool
from pydantic import PrivateAttr


class IntermediateTool(BaseTool):
    name: str = "save_intermediate_result"
    description: str = (
        "保存当前步骤的中间分析结果。"
        "当你完成一个分析步骤后，用此工具记录结论，便于后续步骤引用。"
        "输入格式：一段文字描述当前步骤的分析结论。"
    )

    _store: list = PrivateAttr(default_factory=list)

    def _run(self, result: str) -> str:
        self._store.append(result)
        print(f"\n📝 [中间结果 #{len(self._store)}] {result}\n")
        return f"已保存，当前共 {len(self._store)} 条中间结果"
