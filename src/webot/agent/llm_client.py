import json
import os
import re

from ..utils import get_logger

logger = get_logger(__name__)


def _find_project_root():
    path = os.path.dirname(os.path.abspath(__file__))
    for _ in range(3):
        path = os.path.dirname(path)
    return path


def _load_api_key():
    project_root = _find_project_root()
    env_path = os.path.join(project_root, ".env")

    if not os.path.exists(env_path):
        logger.warning(f".env 文件不存在: {env_path}，LLM 功能不可用")
        return ""

    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
        key = os.getenv("DEEPSEEK_API_KEY")
        if key:
            return key
    except Exception:
        pass

    try:
        raw = open(env_path, encoding="utf-8").read()
        m = re.search(r'DEEPSEEK_API_KEY\s*=\s*["\']?([^"\';\s]+)', raw)
        if m:
            return m.group(1)
    except Exception:
        pass

    logger.warning(".env 中未找到 DEEPSEEK_API_KEY")
    return ""


class LLMClient:
    def __init__(self, api_key=None, model="deepseek-chat"):
        self.model = model
        self._available = False
        self.client = None
        key = api_key or _load_api_key()
        if not key:
            logger.warning("缺少 API Key，LLM 智能回复不可用（可使用模板匹配模式）")
            return
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=key,
                base_url="https://api.deepseek.com",
            )
            self._available = True
            logger.info(f"LLMClient 初始化成功: model={model}")
        except Exception as e:
            logger.warning(f"LLM 客户端初始化失败: {e}")

    @property
    def available(self):
        return self._available and self.client is not None

    def chat(self, messages, tools=None, tool_choice="auto"):
        if not self.available:
            raise RuntimeError("LLM 客户端不可用（未配置 API Key）")
        kwargs = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice

        resp = self.client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message

        if msg.tool_calls:
            return {
                "type": "tool_calls",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments),
                    }
                    for tc in msg.tool_calls
                ],
            }

        return {
            "type": "text",
            "content": msg.content or "",
            "tool_calls": [],
        }
