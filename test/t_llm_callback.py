"""Demo: DeepSeek API tool/function calling.

用法:
    pytest test/t_llm_callback.py -v
    python test/t_llm_callback.py

依赖: pip install openai python-dotenv
API Key 放在 .env 文件中:

    DEEPSEEK_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

"""

import json
import os
import re
from pathlib import Path
from openai import OpenAI

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def _load_api_key() -> str:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        raise RuntimeError(f".env not found at {env_path}")

    # standard dotenv
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
        key = os.getenv("DEEPSEEK_API_KEY")
        if key:
            return key
    except Exception:
        pass

    # fallback: parse non-standard .env (e.g. wrapped in extra quotes)
    raw = env_path.read_text(encoding="utf-8")
    m = re.search(r'DEEPSEEK_API_KEY\s*=\s*["\']?([^"\';\s]+)', raw)
    if m:
        return m.group(1)

    raise RuntimeError("DEEPSEEK_API_KEY not found in .env")

client = OpenAI(
    api_key=_load_api_key(),
    base_url="https://api.deepseek.com",
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的当前天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，如 北京、上海",
                    },
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "执行数学计算",
            "parameters": {
                "type": "object",
                "properties": {
                    "expr": {
                        "type": "string",
                        "description": "数学表达式，如 123*456",
                    },
                },
                "required": ["expr"],
            },
        },
    },
]


def execute_tool(name: str, args: dict) -> str:
    if name == "get_weather":
        return json.dumps({
            "city": args["city"],
            "temperature": 22,
            "unit": "celsius",
            "condition": "晴",
        }, ensure_ascii=False)
    if name == "calculate":
        # 仅供演示，实际使用请用 safe eval 库
        result = eval(args["expr"], {"__builtins__": {}}, {})
        return json.dumps({"expr": args["expr"], "result": result})
    return json.dumps({"error": f"unknown tool: {name}"})


def test_deepseek_tool_call():
    messages: list[dict] = [
        {"role": "system", "content": "你是一个智能助手，可以使用工具回答问题。"},
        {"role": "user", "content": "北京今天天气怎么样？顺便算一下 123 * 456 等于多少？"},
    ]

    # ---- round 1: model returns tool_calls ----
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
    )
    msg = resp.choices[0].message

    print(f"\n[助手] {msg.content or ''}")
    assert msg.tool_calls, "模型应当返回 tool_calls"

    messages.append(msg)  # 加入 assistant 消息（含 tool_calls）

    for tc in msg.tool_calls:
        fn = tc.function
        args = json.loads(fn.arguments)
        print(f"  └─ 调用工具: {fn.name}({args})")

        result = execute_tool(fn.name, args)
        print(f"     └─ 结果: {result}")

        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": result,
        })

    # ---- round 2: model generates final answer with tool results ----
    final = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=TOOLS,
    )
    answer = final.choices[0].message.content
    print(f"\n[最终回复] {answer}")
    assert answer, "应当有最终回复"


if __name__ == "__main__":
    test_deepseek_tool_call()
