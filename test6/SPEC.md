# MiniClaw WeLink CLI AI 助理 — 技术规范（SPEC）

> 本文档是 `welinkcli_agent.py` 的**实现契约**。目标：开发者（或 AI 编码助手）仅凭此文档即可从零写出功能等价的代码，无需查看现有源码。

---

## 1. 项目概述

MiniClaw 是一个 WeLink 群聊 AI 助理。它定时轮询指定 WeLink 群的新消息，用 CrewAI Agent 生成回复，再发回群里。支持纯文本对话、图片理解（多模态）和可扩展的专业技能（如会议纪要）。

### 实现约束

- **单文件**：所有逻辑集中在 `test6/welinkcli_agent.py`，用注释分隔线划分模块，降低阅读门槛。
- **LLM 复用**：不自己实现 LLM，从项目根目录 [`llm/llm.py`](../llm/llm.py) 导入 `LoggedLLM`（带请求日志、重试、多模态支持）。
- **消息收发**：通过外部命令行工具 `welink-cli`（子进程调用），不直连 WeLink API。
- **配置**：从根目录 `.env` 读取，`load_dotenv` 加载。

### 验收标准

| # | 场景 | 期望结果 |
|---|------|---------|
| AC1 | 群内发文本"你好" | 10 秒内收到 `【AI助手】` 开头的回复 |
| AC2 | 群内发图片 + 文字 | Agent 能"看到"图片并针对图片内容回复 |
| AC3 | 同一条消息 | 只回复一次（重启后也不重复） |
| AC4 | 发送自身回复 / 单字符消息 | 不触发回复，也不阻塞后续消息 |
| AC5 | welink-cli 不可用或返回异常 JSON | 不崩溃，下一轮继续轮询 |
| AC6 | LLM 调用失败 | 该消息跳过，不发送，进程继续 |
| AC7 | `Ctrl+C` | 优雅退出 |

---

## 2. 架构与数据流

```
WeLink 群（文本/图片）
   │  welink-cli im query-history-message  （每 CHECK_INTERVAL 秒轮询）
   ▼
get_recent_messages()  ──解析 JSON──▶  list[InboundMessage]（按时间降序）
   │
   ▼
取 messages[0]（最新一条）
   │  去重（RepliedTracker）+ 过滤（过短/自身回复）
   ▼
build_prompt()  ──若有图片，download_image() 下载到本地──▶  prompt 字符串
   │
   ▼
handle_message()  ──▶  Main Agent.kickoff(prompt)
   │                     ├─ FileWriterTool / FileReadTool
   │                     ├─ AddImageTool（图片→base64）
   │                     └─ SkillLoaderTool（会议纪要/图片分析 Sub-Crew）
   ▼
send_to_group()  ──▶  welink-cli im send-to-group（带【AI助手】前缀）
   │
   ▼
tracker.mark_replied()  ──▶  持久化到 replied_msgs.json
```

---

## 3. 单文件模块布局

`welinkcli_agent.py` 按以下顺序自上而下组织，每块用 `# ─── 区块名 ───` 注释分隔。**实现时严格保持此顺序**（后定义的依赖先定义的）：

```
1. 模块 docstring + __version__ + imports
2. .env 加载（project_root / load_dotenv）
3. 日志配置（logging.basicConfig + logger）
4. 配置        _env_int() / Config / config
5. 消息模型    InboundMessage
6. 工具        AddImageTool
7. 技能配置    SKILLS
8. 技能加载器  SkillLoaderTool
9. Agent       create_main_agent()
10. WeLink CLI run_welink_command / get_recent_messages / download_image / REPLY_PREFIX / send_to_group
11. 已回复追踪 RepliedTracker
12. 消息处理    handle_message / build_prompt
13. 主循环      main()
14. if __name__ == "__main__": main()
```

---

## 4. 外部接口契约（welink-cli）

程序通过 `subprocess.run(["welink-cli", ...])` 调用外部 CLI。需约定的命令与返回格式如下。

### 4.1 拉取历史消息

```
welink-cli im query-history-message --group-id <GROUP_ID> --query-count 50
```

**stdout** 是一段 JSON，结构：

```jsonc
{
  "respData": {
    "chatInfo": [
      {
        "msgId": "979178...",            // 消息ID（字符串）
        "content": "你好",               // 文本内容（图片消息可能为空）
        "image_url": "https://...",      // 图片URL，可能键名为 imageUrl，无图时缺省/空
        "senderName": "张三",            // 发送者，可能键名为 sender
        "serverSendTime": 1750000000000  // 服务端发送时间，毫秒级 epoch
      }
    ]
  }
}
```

**健壮性要求**：`respData` 或 `chatInfo` 可能为 `null` 或缺省；顶层可能不是 dict。任何结构异常都不能抛出，统一返回空列表。

### 4.2 发送群消息

```
welink-cli im send-to-group --group-id <GROUP_ID> --text "<REPLY_PREFIX><回复内容>"
```

成功时 `stdout` 非空（不为 `None` 即视为成功）。

### 4.3 通用调用约定

- 子进程超时：`30` 秒。
- 编码：`encoding="utf-8", errors="ignore"`，避免 Windows 乱码。
- 任何异常（命令不存在、超时、非零退出）都**捕获并降级**，不得中断主循环。

---

## 5. 模块实现契约

### 5.1 配置 `_env_int` / `Config`

```python
def _env_int(name: str, default: int) -> int
```
- 环境变量缺省或空串 → 返回 `default`。
- 值非整数 → 启动期直接 `raise RuntimeError(f"{name} 必须为整数，当前值: {raw!r}")`，不延后到运行期。

```python
class Config:
    OPENAI_MODEL:    str = os.getenv("OPENAI_MODEL", "deepseek-v4-pro")
    OPENAI_API_KEY:  str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_API_BASE: str = os.getenv("OPENAI_API_BASE", "https://api.deepseek.com/v1")
    WELINK_GROUP_ID: str = os.getenv("WELINK_GROUP_ID", "")
    CHECK_INTERVAL:  int = _env_int("CHECK_INTERVAL", 30)
    RECENT_MINUTES:  int = _env_int("RECENT_MINUTES", 30)
    WORKSPACE:       Path = Path(__file__).parent / "workspace"

    def ensure_workspace(self, group_id: str) -> Path
```
> 注：以上为代码内兜底默认值，实际取值以根目录 `.env` 为准（见 §7）。

`ensure_workspace`：创建 `workspace/{group_id}/images` 与 `workspace/{group_id}/files` 目录（`parents=True, exist_ok=True`），返回 `workspace/{group_id}`。

模块级实例：`config = Config()`。

### 5.2 消息模型 `InboundMessage`（Pydantic `BaseModel`）

```python
class InboundMessage(BaseModel):
    group_id: str
    content: str
    image_url: Optional[str] = None
    msg_id: str
    sender_name: str

    @property
    def has_image(self) -> bool          # image_url is not None

    @classmethod
    def from_raw(cls, group_id: str, raw: dict) -> "InboundMessage"
```

`from_raw` 字段映射（带兜底）：

| 字段 | 取值 | 兜底 |
|------|------|------|
| `content` | `raw.get("content", "") or ""` | 空串 |
| `image_url` | `raw.get("image_url") or raw.get("imageUrl")` | `None` |
| `msg_id` | `str(raw.get("msgId", ""))` | 空串 |
| `sender_name` | `raw.get("senderName", raw.get("sender", "未知"))` | `"未知"` |

### 5.3 LLM `LoggedLLM`（导入，不实现）

```python
from llm.llm import LoggedLLM
```
在 `main()` 中构造，**必须显式传 `model`**（CrewAI 的 `LLM.__new__` 在 `__init__` 之前执行，缺 model 会报 `missing model`）：

```python
llm = LoggedLLM(
    model=config.OPENAI_MODEL,
    base_url=config.OPENAI_API_BASE,
    api_key=config.OPENAI_API_KEY,
)
```
需在文件头部把项目根加入 `sys.path`：`sys.path.insert(0, str(Path(__file__).resolve().parent.parent))`。

### 5.4 工具 `AddImageTool`（`crewai.tools.BaseTool`）

```python
class AddImageTool(BaseTool):
    name: str = "add_image"
    description: str = "加载图片到上下文...输入图片文件路径，返回 base64 编码的图片数据。"

    def _run(self, image_path: str) -> str
```
行为：
- 文件不存在 → 返回 `f"错误：图片不存在 {image_path}"`，并 `logger.warning`。
- 读取文件 → base64 编码 → 返回 `f"data:image/{ext};base64,{data}"`，`ext` 取 `path.suffix[1:]`，缺省为 `"png"`。
- 记录日志：图片名与大小（KB）。

### 5.5 技能配置 `SKILLS`

一个模块级 list，每项结构固定：

```python
{
    "name": str,                 # 技能唯一标识，供 SkillLoaderTool 查找
    "type": "task",              # 固定
    "description": str,          # 技能用途
    "input_schema":  {字段名: 说明},
    "output_schema": {字段名: 说明},
}
```

必须包含两项：`meeting_summary`（整理会议纪要）和 `image_analyzer`（分析图片内容）。具体字段见现有实现。

### 5.6 技能加载器 `SkillLoaderTool`（`BaseTool`）

```python
class SkillLoaderTool(BaseTool):
    name: str = "skill_loader"
    description: str = "加载并执行预定义技能..."
    skills: list[dict[str, Any]]   # pydantic 字段
    llm: Any                        # pydantic 字段（类型用 Any，避免 crewai LLM 包装校验失败）

    def _run(self, skill_name: str, **kwargs: Any) -> str
    def _find_skill(self, skill_name: str) -> dict[str, Any] | None
    def _execute_skill(self, skill: dict, inputs: dict) -> str
```
行为：
- `_run`：找不到技能 → 返回错误串（列出可用技能名）。
- `_execute_skill`：为该技能动态创建一个 **Sub-Crew**（一个 `Agent` + 一个 `Task` + 一个 `Crew`），把 `input_schema`/`output_schema` 序列化进 Task 描述与期望输出，`crew.kickoff()` 后返回 `str(result)`。

### 5.7 Agent `create_main_agent(llm) -> Agent`

```python
def create_main_agent(llm: LoggedLLM) -> Agent
```
- `role="WeLink 办公助手"`，`goal` 围绕日常办公 + 图片理解。
- `backstory`：说明四项能力（问答 / 看图 / 读写文件 / 调技能）与工作流（有图先 `add_image`）。
- `tools=[FileWriterTool(), FileReadTool(), AddImageTool(), SkillLoaderTool(skills=SKILLS, llm=llm)]`。
- `llm=llm`, `verbose=True`, `multimodal=True`。

### 5.8 WeLink CLI 函数

```python
def run_welink_command(args: list[str]) -> tuple[Optional[str], Optional[str]]
```
按 §4.3 约定调用；异常时 `logger.error` 并返回 `(None, str(e))`。

```python
def get_recent_messages(group_id: str, minutes: int = 30) -> list[InboundMessage]
```
- 调 `query-history-message`（query-count 50）。
- 解析 `respData.chatInfo`（用 `or {}` / `or []` 防 None）。
- 过滤 `serverSendTime >= now_ms - minutes*60*1000` 的消息。
- **按 `serverSendTime` 降序排序**（保证 `messages[0]` 是最新）。
- 解析异常（`JSONDecodeError`/`KeyError`/`TypeError`）→ `logger.error` 并返回 `[]`。

```python
def download_image(image_url: str, save_path: Path) -> Optional[Path]
```
`requests.get(timeout=30)` → `raise_for_status` → 写入文件；建父目录；异常返回 `None`。

```python
REPLY_PREFIX = "【AI助手】"

def send_to_group(group_id: str, text: str) -> bool
```
发送 `f"{REPLY_PREFIX}{text}"`；`stdout is None` 视为失败返回 `False`。

### 5.9 已回复追踪 `RepliedTracker`

```python
class RepliedTracker:
    def __init__(self, workspace: Path) -> None   # file = workspace/"replied_msgs.json"
    def is_replied(self, msg_id: str) -> bool
    def mark_replied(self, msg_id: str) -> None    # 加入集合并立即 _save()
    def _load(self) -> set[str]                    # 读 JSON list → set；失败返回空集
    def _save(self) -> None                        # set → JSON list，ensure_ascii=False
```
- 持久化格式：JSON 数组，UTF-8。
- 加载失败只 warning，不抛错（用旧空集继续）。

### 5.10 消息处理

```python
def handle_message(agent: Agent, prompt: str) -> str | None
```
`agent.kickoff(prompt)` → `str(result)`；异常 → `logger.error` 返回 `None`。

```python
def build_prompt(msg: InboundMessage, images_dir: Path) -> str
```
- 无图 → 返回 `msg.content`。
- 有图 → 下载到 `images_dir / f"{msg.msg_id}.png"`：
  - 下载成功 → 返回 `content + 提示语（告知本地路径，要求用 add_image 工具加载）`。
  - 下载失败 → 返回 `content + "[用户发送了一张图片，但下载失败]"`。

### 5.11 主循环 `main()`

启动：
1. `group_id = config.WELINK_GROUP_ID`，为空 → `raise RuntimeError`。
2. `OPENAI_API_KEY` 为空 → `logger.warning`（不阻断）。
3. `workspace = config.ensure_workspace(group_id)`；`images_dir = workspace/"images"`。
4. 构造 `llm`、`agent`、`tracker`，打印启动日志与已回复记录数。

循环（`while True`，每轮 `time.sleep(config.CHECK_INTERVAL)`）：
1. `messages = get_recent_messages(group_id, config.RECENT_MINUTES)`；空 → 继续监听。
2. `latest = messages[0]`。
3. 已回复 → 继续监听。
4. **过滤**：`len(text) < 2` 或 `text.startswith(REPLY_PREFIX)` → **先 `mark_replied` 再跳过**（否则该消息永远卡在 `[0]`，阻塞队列）。
5. 打印收到消息日志。
6. `prompt = build_prompt(...)`；`reply = handle_message(...)`。
7. `reply` 非空 → `send_to_group` + `mark_replied` + 日志。
8. 异常：`KeyboardInterrupt` → 优雅退出；其他异常 → `logger.error` 后继续。

---

## 6. 日志约定

- `logging.basicConfig`：`INFO` 级别，格式 `[时间] [级别] 消息`。
- 关键事件用 `logger.info`/`error`；轮询空转提示可用 `print`。
- `LoggedLLM` 自带请求/响应日志，无需在本文件重复打印 LLM 报文。

---

## 7. 环境配置

根目录 `.env`（所有 test 共用，本程序用 `load_dotenv` 读取）：

```env
# LLM（默认小鲁班网关，model=auto 对应 Qwen-V3.5-35B-A3B 多模态）
OPENAI_MODEL=auto
OPENAI_API_KEY=你的密钥
OPENAI_API_BASE=http://xiaoluban.rnd.huawei.com:80/y/llm/v1
OTEL_SDK_DISABLED=true
NO_PROXY=xiaoluban.rnd.huawei.com

# WeLink
WELINK_GROUP_ID=your-group-id-here
CHECK_INTERVAL=10
RECENT_MINUTES=10
```

---

## 8. 项目结构

```
miniclaw_course/
├── .env                       # 环境变量（共用）
├── pyproject.toml             # 依赖
├── requirements.txt           # 依赖（pip）
├── llm/llm.py                 # LoggedLLM（本程序导入）
└── test6/
    ├── welinkcli_agent.py     # 本规范的目标产物（单文件）
    ├── welinkcli_llm.py       # 直接 LLM 调用版（对比参考）
    ├── SPEC.md                # 本文档
    └── README.md              # 开发流程指南
```

运行时自动生成：

```
test6/workspace/{group_id}/
├── images/            # 下载的图片
├── files/             # Agent 写出的文件
└── replied_msgs.json  # 已回复消息记录
```

---

## 9. 依赖

| 包 | 用途 |
|---|------|
| `crewai` | Agent / Crew / Task 框架 |
| `crewai-tools` | `FileReadTool` / `FileWriterTool` |
| `pydantic` | `InboundMessage` 数据模型 |
| `requests` | 图片下载 |
| `python-dotenv` | 读取 `.env` |

> `LoggedLLM` 依赖根目录 `llm/llm.py`，运行时需能 `import llm.llm`。

---

## 10. 扩展指南

**新增技能**：往 `SKILLS` 追加一项（含 name/description/input_schema/output_schema），Sub-Crew 自动可用。

**新增工具**：继承 `BaseTool`，实现 `_run`，加入 `create_main_agent` 的 `tools` 列表。

**支持新消息类型**：扩展 `InboundMessage` 字段与 `from_raw` 映射，并在 `build_prompt` 中处理。

---

## 11. 常见问题

**Q: 轮询延迟？** 默认 `CHECK_INTERVAL=10` 秒，延迟 ≤10 秒。过小会频繁请求。

**Q: Agent 版 vs 直接 LLM 版？** `welinkcli_agent.py` 走 CrewAI Agent（工具/多步推理/技能）；`welinkcli_llm.py` 直接 `requests.post` 调 LLM，仅作对比。

**Q: 如何调试？** `verbose=True` 看 Agent 思考；`LoggedLLM` 自动打印 LLM 请求/响应。
