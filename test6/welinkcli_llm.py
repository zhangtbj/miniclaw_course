import os
import sys
import time
import json
import subprocess
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# ========== 配置区（从根目录 .env 读取） ==========
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

load_dotenv(project_root / ".env")

def _env_int(name, default):
    """读取整数型环境变量，非法值在启动期即报错。"""
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        raise RuntimeError(f"{name} 必须为整数，当前值: {raw!r}")


GROUP_ID = os.getenv("WELINK_GROUP_ID", "")
CHECK_INTERVAL = _env_int("CHECK_INTERVAL", 30)
RECENT_MINUTES = _env_int("RECENT_MINUTES", 30)

MODEL_ID = os.getenv("OPENAI_MODEL", "deepseek-v4-pro")
BASE_URL = os.getenv("OPENAI_API_BASE", "https://api.deepseek.com/v1")
API_KEY = os.getenv("OPENAI_API_KEY", "")

# 已回复消息记录文件
REPLIED_FILE = Path(__file__).parent / "replied_msgs.json"


# ========== 基础工具函数 ==========

def run_welink_command(args):
    """调用 welink-cli 命令"""
    try:
        cmd = ["welink-cli"] + args
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=30, encoding='utf-8', errors='ignore'
        )
        return result.stdout, result.stderr
    except Exception as e:
        return None, str(e)


def get_recent_messages(group_id, minutes=30):
    """拉取群最近N分钟的消息"""
    stdout, stderr = run_welink_command([
        "im", "query-history-message",
        "--group-id", group_id,
        "--query-count", "50"
    ])

    if not stdout:
        return []

    try:
        data = json.loads(stdout)
        resp_data = data.get('respData') or {}
        chat_info = resp_data.get('chatInfo') or []

        now_ms = int(datetime.now().timestamp() * 1000)
        cutoff_ms = now_ms - (minutes * 60 * 1000)

        messages = []
        for msg in chat_info:
            server_time = msg.get('serverSendTime', 0)
            if server_time >= cutoff_ms:
                messages.append(msg)
        # 按发送时间降序排序，确保 messages[0] 为最新消息
        messages.sort(key=lambda m: m.get('serverSendTime', 0), reverse=True)
        return messages
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] 解析消息失败: {e}")
        return []


def send_to_group(group_id, text):
    """发送消息到群"""
    stdout, stderr = run_welink_command([
        "im", "send-to-group",
        "--group-id", group_id,
        "--text", f"【AI助手】{text}"
    ])
    return stdout is not None


def load_replied_msgs():
    """加载已回复的消息ID集合"""
    if REPLIED_FILE.exists():
        try:
            with open(REPLIED_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()


def save_replied_msgs(replied_set):
    """持久化已回复的消息ID"""
    try:
        with open(REPLIED_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(replied_set), f, ensure_ascii=False)
    except Exception:
        pass


# ========== LLM 调用 ==========

def call_llm(user_message):
    """调用大模型生成回复"""
    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        prompt = f"""你是一个技术支持助手，请根据用户的问题给出详细、实用的解答。

用户问题：{user_message}

请给出清晰的解决方案。如果信息不足，请根据你的技术知识尽量帮助他。"""

        data = {
            "model": MODEL_ID,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }

        response = requests.post(
            f"{BASE_URL}/chat/completions",
            headers=headers,
            json=data,
            timeout=120
        )

        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            print(f"[ERROR] LLM调用失败: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        print(f"[ERROR] LLM调用异常: {e}")
        return None


# ========== 主循环 ==========

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] 群消息监听启动，监听群: {GROUP_ID}")

    replied_msgs = load_replied_msgs()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] 已加载 {len(replied_msgs)} 条已回复记录")

    while True:
        try:
            # 1. 拉取群最近N分钟消息
            messages = get_recent_messages(GROUP_ID, RECENT_MINUTES)

            if not messages:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] 群中无任何消息，继续监听")
                time.sleep(CHECK_INTERVAL)
                continue

            # 取最新一条消息
            latest_msg = messages[0]
            msg_id = str(latest_msg.get('msgId', ''))

            # 2. 判断是否已回复过
            if msg_id in replied_msgs:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] 群中无未回复消息，继续监听")
                time.sleep(CHECK_INTERVAL)
                continue

            # 3. 过滤无效消息（标记 replied 避免重复处理导致队列卡死）
            text = latest_msg.get('content', '') or ''
            if len(text) < 2 or text.startswith('【AI助手】'):
                replied_msgs.add(msg_id)
                save_replied_msgs(replied_msgs)
                time.sleep(CHECK_INTERVAL)
                continue

            sender = latest_msg.get('senderName', latest_msg.get('sender', '未知'))
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] 收到消息 - 发送者: {sender} | 内容: {text[:80]}...")

            # 4. 调用LLM生成回复
            reply = call_llm(text)
            if reply:
                # 5. 发送到群
                send_to_group(GROUP_ID, reply)
                # 6. 记录已回复
                replied_msgs.add(msg_id)
                save_replied_msgs(replied_msgs)
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] 已回复并标记 msgId={msg_id}")

            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("\n[INFO] 已停止监听")
            break
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] 异常: {e}")
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
