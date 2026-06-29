import os
from crewai import LLM, Agent, Task

# ==============================================================================
# LLM 配置示例
# ==============================================================================
# 使用 CrewAI 的 LLM 类配置 OpenAI 兼容接口：https://docs.crewai.com/en/concepts/llms
# 适用于：DeepSeek、GLM、OpenAI 等支持 OpenAI 格式的 API

llm = LLM(
    model=os.getenv("OPENAI_MODEL", "deepseek-v4-pro"),
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_API_BASE"),  # API 基础地址
)

# ==============================================================================
# LLM 直接调用示例
# ==============================================================================
# 演示如何直接调用 LLM，不通过 Agent

prompt = "预测2026年世界杯冠军是谁？只回答一个国家名和一句话理由。"
response = llm.call([{"role": "user", "content": prompt}])
print(response)


# ==============================================================================
# Agent 使用 LLM 示例
# ==============================================================================
# 演示如何将配置好的 LLM 传递给 Agent

agent = Agent(
    role="足球预测员",
    goal="快速给出足球赛事预测结论",
    backstory="你是足球预测专家，回答简洁有力。",
    llm=llm,
    verbose=True,
)

task = Task(
    description="预测2026年世界杯冠军，只回答一个国家名和一句话理由。",
    expected_output="国家名 + 一句话理由，不超过30字。",
    agent=agent,
)

result = agent.execute_task(task)
print(result)

