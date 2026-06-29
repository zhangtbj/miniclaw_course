"""
LLM 模块

提供自定义 LLM 实现，兼容 OpenAI 格式接口（DeepSeek、通义千问、GLM 等）。

主要组件：
- LoggedLLM：带完整请求日志的通用 LLM 实现
"""
from .llm import LoggedLLM

__all__ = ['LoggedLLM']
