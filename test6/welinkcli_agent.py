"""MiniClaw WeLink CLI AI 助理 — 单文件版本。

单 Agent + 多工具 + 技能加载器，集成文本对话、图片理解与技能扩展。
启动流程：创建 CrewAI Agent → 轮询群消息 → 去重 → Agent 处理 → 发送回复。
"""

__version__ = "0.1.0"

import base64
import json
import logging
import os
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
import requests
from crewai import Agent, Crew, Task
from crewai.tools import BaseTool
from crewai_tools import FileReadTool, FileWriterTool
from pydantic import BaseModel

from llm.llm import LoggedLLM

# ========== 配置区（从根目录 .env 读取） ==========
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

load_dotenv(project_root / ".env")

# ──────────────────────────── 日志 ────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ──────────────────────────── 配置 ────────────────────────────


def _env_int(name: str, default: int) -> int:
    """读取整数型环境变量，非法值在启动期即报错而非运行期。"""
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        raise RuntimeError(f"{name} 必须为整数，当前值: {raw!r}")


class Config:
    """集中管理所有运行时配置项。"""

    # LLM 模型配置
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "deepseek-v4-pro")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_API_BASE: str = os.getenv("OPENAI_API_BASE", "https://api.deepseek.com/v1")

    # WeLink 配置
    WELINK_GROUP_ID: str = os.getenv("WELINK_GROUP_ID", "")
    CHECK_INTERVAL: int = _env_int("CHECK_INTERVAL", 30)
    RECENT_MINUTES: int = _env_int("RECENT_MINUTES", 30)

    # 运行时工作空间
    WORKSPACE: Path = Path(__file__).parent / "workspace"

    def ensure_workspace(self, group_id: str) -> Path:
        """确保群工作目录存在，返回群工作目录路径。

        目录结构：workspace/{group_id}/{images,files}
        """
        base = self.WORKSPACE / group_id
        (base / "images").mkdir(parents=True, exist_ok=True)
        (base / "files").mkdir(parents=True, exist_ok=True)
        return base


config = Config()


# ──────────────────────────── 消息模型 ────────────────────────────


class InboundMessage(BaseModel):
    """单条入站消息（文本或图片）。"""

    group_id: str
    content: str
    image_url: Optional[str] = None
    msg_id: str
    sender_name: str

    @property
    def has_image(self) -> bool:
        """是否携带图片。"""
        return self.image_url is not None

    @classmethod
    def from_raw(cls, group_id: str, raw: dict) -> "InboundMessage":
        """从 welink-cli 返回的原始消息字典构造 InboundMessage。"""
        return cls(
            group_id=group_id,
            content=raw.get("content", "") or "",
            image_url=raw.get("image_url") or raw.get("imageUrl"),
            msg_id=str(raw.get("msgId", "")),
            sender_name=raw.get("senderName", raw.get("sender", "未知")),
        )
class AddImageTool(BaseTool):
    """将本地图片转为 base64 data URI，供多模态 LLM 理解图片内容。"""

    name: str = "add_image"
    description: str = (
        "加载图片到上下文，用于分析图片内容。"
        "输入图片文件路径，返回 base64 编码的图片数据。"
    )

    def _run(self, image_path: str) -> str:
        """读取图片并转为 data URI。"""
        path = Path(image_path)
        if not path.exists():
            logger.warning("图片不存在: %s", image_path)
            return f"错误：图片不存在 {image_path}"

        with open(path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()

        ext = path.suffix[1:] or "png"
        logger.info("已加载图片: %s (%.2f KB)", path.name, path.stat().st_size / 1024)
        return f"data:image/{ext};base64,{image_data}"


# ──────────────────────────── 工具：技能加载器 ────────────────────────────

# 技能配置：每项定义一个可由 Sub-Crew 执行的专业任务
SKILLS = [
    {
        "name": "meeting_summary",
        "type": "task",
        "description": "将杂乱的会议记录整理为结构化纪要",
        "input_schema": {"raw_notes": "原始会议记录文本"},
        "output_schema": {
            "attendees": "参会人列表",
            "key_decisions": "关键决策",
            "action_items": "待办事项",
        },
    },
    {
        "name": "image_analyzer",
        "type": "task",
        "description": "分析图片内容，提取关键信息",
        "input_schema": {"image_path": "图片文件路径"},
        "output_schema": {
            "description": "图片描述",
            "key_elements": "关键元素列表",
            "text_content": "图中的文字（如有）",
        },
    },
]


class SkillLoaderTool(BaseTool):
    """根据技能名加载预配置技能，创建一次性 Sub-Crew 执行任务并返回结果。"""

    name: str = "skill_loader"
    description: str = (
        "加载并执行预定义技能。传入技能名与对应参数，"
        "技能将以结构化方式处理任务并返回结果。"
    )
    skills: list[dict[str, Any]]
    llm: Any

    def _run(self, skill_name: str, **kwargs: Any) -> str:
        """执行指定技能。"""
        skill = self._find_skill(skill_name)
        if skill is None:
            available = [s["name"] for s in self.skills]
            return f"错误：未找到技能 '{skill_name}'，可用技能: {available}"
        return self._execute_skill(skill, kwargs)

    def _find_skill(self, skill_name: str) -> dict[str, Any] | None:
        """按名称查找技能配置。"""
        return next((s for s in self.skills if s["name"] == skill_name), None)

    def _execute_skill(self, skill: dict[str, Any], inputs: dict[str, Any]) -> str:
        """创建 Sub-Crew 执行单个技能任务。"""
        input_desc = json.dumps(skill.get("input_schema", {}), ensure_ascii=False)
        output_desc = json.dumps(skill.get("output_schema", {}), ensure_ascii=False)

        sub_agent = Agent(
            role=f"{skill['name']} 专家",
            goal=skill["description"],
            backstory=f"你专注于：{skill['description']}。请严格按输出格式返回结果。",
            llm=self.llm,
            verbose=True,
        )

        task = Task(
            description=(
                f"处理以下输入：{json.dumps(inputs, ensure_ascii=False)}\n"
                f"输入字段说明：{input_desc}\n"
                f"输出字段要求：{output_desc}"
            ),
            expected_output=f"符合 {output_desc} 结构的 JSON 结果",
            agent=sub_agent,
        )

        crew = Crew(agents=[sub_agent], tasks=[task], verbose=True)
        logger.info("执行技能: %s", skill["name"])
        return str(crew.kickoff())


# ──────────────────────────── Agent ────────────────────────────


def create_main_agent(llm: LoggedLLM) -> Agent:
    """创建主 Agent。

    Args:
        llm: 已配置的 LoggedLLM 实例

    Returns:
        配置好工具与技能的 CrewAI Agent
    """
    return Agent(
        role="WeLink 办公助手",
        goal="帮助用户处理日常办公事务，支持文本对话和图片理解",
        backstory="""
        你是一位高效的 WeLink 办公助手，擅长：
        1. 理解和回答用户的问题
        2. 分析用户发送的图片（如截图、文档照片）
        3. 使用工具读写文件
        4. 调用专业技能处理复杂任务（如整理会议纪要）

        工作流程：
        - 如果用户发送了图片，先调用 add_image 加载图片
        - 根据用户需求选择合适的工具或技能
        - 返回清晰、结构化的结果
        """,
        tools=[
            FileWriterTool(),
            FileReadTool(),
            AddImageTool(),
            SkillLoaderTool(skills=SKILLS, llm=llm),
        ],
        llm=llm,
        verbose=True,
        multimodal=True,
    )


# ──────────────────────────── WeLink CLI ────────────────────────────


def run_welink_command(args: list[str]) -> tuple[Optional[str], Optional[str]]:
    """调用 welink-cli 命令。"""
    try:
        result = subprocess.run(
            ["welink-cli", *args],
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="ignore",
        )
        return result.stdout, result.stderr
    except Exception as e:
        logger.error("welink-cli 调用失败: %s", e)
        return None, str(e)


def get_recent_messages(group_id: str, minutes: int = 30) -> list[InboundMessage]:
    """通过 welink-cli 拉取群最近 N 分钟的消息。"""
    stdout, _ = run_welink_command(
        ["im", "query-history-message", "--group-id", group_id, "--query-count", "50"]
    )
    if not stdout:
        return []

    try:
        data = json.loads(stdout)
        resp_data = data.get("respData") or {}
        chat_info = resp_data.get("chatInfo") or []

        now_ms = int(datetime.now().timestamp() * 1000)
        cutoff_ms = now_ms - (minutes * 60 * 1000)

        recent = [msg for msg in chat_info if msg.get("serverSendTime", 0) >= cutoff_ms]
        recent.sort(key=lambda m: m.get("serverSendTime", 0), reverse=True)

        return [InboundMessage.from_raw(group_id, msg) for msg in recent]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error("解析消息失败: %s", e)
        return []


def download_image(image_url: str, save_path: Path) -> Optional[Path]:
    """下载图片到本地路径。"""
    try:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        resp = requests.get(image_url, timeout=30)
        resp.raise_for_status()
        save_path.write_bytes(resp.content)
        return save_path
    except Exception as e:
        logger.error("下载图片失败: %s", e)
        return None


REPLY_PREFIX = "【AI助手】"


def send_to_group(group_id: str, text: str) -> bool:
    """发送文本消息到指定群。"""
    stdout, stderr = run_welink_command(
        ["im", "send-to-group", "--group-id", group_id, "--text", f"{REPLY_PREFIX}{text}"]
    )
    if stdout is None:
        logger.error("发送失败: %s", stderr)
        return False
    return True


# ──────────────────────────── 已回复追踪 ────────────────────────────


class RepliedTracker:
    """管理已回复消息ID集合，支持持久化到 JSON 文件。"""

    def __init__(self, workspace: Path) -> None:
        self.file: Path = workspace / "replied_msgs.json"
        self.replied: set[str] = self._load()

    def is_replied(self, msg_id: str) -> bool:
        """判断消息是否已回复。"""
        return msg_id in self.replied

    def mark_replied(self, msg_id: str) -> None:
        """标记消息为已回复并持久化。"""
        self.replied.add(msg_id)
        self._save()

    def _load(self) -> set[str]:
        """从磁盘加载已回复集合。"""
        if self.file.exists():
            try:
                with open(self.file, "r", encoding="utf-8") as f:
                    return set(json.load(f))
            except Exception as e:
                logger.warning("加载已回复记录失败: %s", e)
        return set()

    def _save(self) -> None:
        """持久化已回复集合到磁盘。"""
        try:
            self.file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file, "w", encoding="utf-8") as f:
                json.dump(list(self.replied), f, ensure_ascii=False)
        except Exception as e:
            logger.error("保存已回复记录失败: %s", e)


# ──────────────────────────── 消息处理 ────────────────────────────


def handle_message(agent: Agent, prompt: str) -> str | None:
    """调用 Agent 生成回复。"""
    try:
        result = agent.kickoff(prompt)
        return str(result)
    except Exception as e:
        logger.error("Agent 执行失败: %s", e)
        return None


def build_prompt(msg: InboundMessage, images_dir: Path) -> str:
    """根据消息构造 Agent 输入提示；若有图片则下载并提示 Agent 使用 add_image 工具。"""
    image_url = msg.image_url
    if image_url is None:
        return msg.content

    image_path = images_dir / f"{msg.msg_id}.png"
    saved = download_image(image_url, image_path)
    if saved is None:
        return f"{msg.content}\n\n[用户发送了一张图片，但下载失败]"

    return (
        f"{msg.content}\n\n"
        f"[用户发送了一张图片，本地路径: {saved}。请使用 add_image 工具加载并分析该图片。]"
    )


# ──────────────────────────── 主循环 ────────────────────────────


def main() -> None:
    """主循环：轮询群消息并自动回复。"""
    group_id = config.WELINK_GROUP_ID
    if not group_id:
        raise RuntimeError("WELINK_GROUP_ID 未配置，请检查 .env")

    if not config.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY 未配置，LLM 调用可能失败")

    workspace = config.ensure_workspace(group_id)
    images_dir = workspace / "images"
    llm = LoggedLLM(
        model=config.OPENAI_MODEL,
        base_url=config.OPENAI_API_BASE,
        api_key=config.OPENAI_API_KEY,
    )
    agent = create_main_agent(llm)
    tracker = RepliedTracker(workspace)

    logger.info("群消息监听启动，监听群: %s", group_id)
    logger.info("已加载 %d 条已回复记录", len(tracker.replied))

    while True:
        try:
            messages = get_recent_messages(group_id, config.RECENT_MINUTES)
            if not messages:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] 群中无任何消息，继续监听")
                time.sleep(config.CHECK_INTERVAL)
                continue

            latest = messages[0]

            if tracker.is_replied(latest.msg_id):
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] 群中无未回复消息，继续监听")
                time.sleep(config.CHECK_INTERVAL)
                continue

            text = latest.content
            if len(text) < 2 or text.startswith(REPLY_PREFIX):
                tracker.mark_replied(latest.msg_id)
                time.sleep(config.CHECK_INTERVAL)
                continue

            logger.info(
                "收到消息 - 发送者: %s | 内容: %s",
                latest.sender_name,
                text[:80],
            )

            prompt = build_prompt(latest, images_dir)
            reply = handle_message(agent, prompt)
            if reply:
                send_to_group(group_id, reply)
                tracker.mark_replied(latest.msg_id)
                logger.info("已回复并标记 msgId=%s", latest.msg_id)

            time.sleep(config.CHECK_INTERVAL)

        except KeyboardInterrupt:
            logger.info("已停止监听")
            break
        except Exception as e:
            logger.error("主循环异常: %s", e)
            time.sleep(config.CHECK_INTERVAL)


if __name__ == "__main__":
    main()
