# WeChat Agent 架构调整方案

> 创建: 2026-06-18
> 状态: 已决策，等待实施

---

## 决策记录

| 问题 | 决策 |
|---|---|
| Memory 存储后端 | 抽象接口 + `JsonLinesBackend` + `SqliteBackend` 双实现 |
| LLM 提供者 | DeepSeek（延续现有 `.env` 配置） |
| 回复策略 | GUI 开关切换：模板匹配 / LLM / LLM+降级 |

---

## 待创建文件（8 个新文件）

| 文件 | 说明 |
|---|---|
| `src/webot/agent/__init__.py` | 包定义 |
| `src/webot/agent/loop.py` | `AgentLoop` 主调度（从 `main.py` 抽出代理逻辑） |
| `src/webot/agent/memory.py` | `Memory` + `JsonLinesBackend` + `SqliteBackend` |
| `src/webot/agent/session.py` | `Session` 会话上下文维护 |
| `src/webot/agent/skill_manager.py` | LLM tool calling 注册/路由 |
| `src/webot/agent/llm_client.py` | DeepSeek API 封装 |
| `src/webot/skills/base.py` | `Skill` 基类 |
| 8 个 `skills/*.py` | 各追加 `*Skill(Skill)` 子类，不删原函数 |

## 待修改文件

| 文件 | 操作 |
|---|---|
| `src/webot/main.py` | 精简为 GUI 呈现层，委托给 `AgentLoop` |
| `pyproject.toml` | 追加 `openai` 依赖 |

## 不涉及的文件

- `test/` 目录及所有 `t_*.py` 测试
- `config.py` / `utils.py`
- `rules.json`
- `images/`

---

## 建议实施步骤

1. `agent/session.py` + `agent/memory.py`（无外部依赖，先搭基础）
2. `skills/base.py` + `agent/skill_manager.py`（skill 框架）
3. 为每个现有 skill 文件增加 `Skill` 子类
4. `agent/llm_client.py`（依赖 openai）
5. `agent/loop.py` + `agent/__init__.py`（核心调度）
6. 修改 `pyproject.toml` 增加 openai 依赖
7. 精简 `main.py`：GUI → AgentLoop 委托
8. 验证 `test/` 下测试不受影响

---

## 关键接口设计（备忘）

### Memory 抽象

```python
class MemoryBackend:
    def save_message(self, chat_name, role, content, metadata=None)
    def get_history(self, chat_name, limit=30) -> list[dict]
    def search(self, query, chat_name=None) -> list[dict]

class JsonLinesBackend(MemoryBackend): ...
class SqliteBackend(MemoryBackend): ...

class Memory:
    def __init__(self, backend: MemoryBackend)
```

### Skill 基类

```python
class Skill:
    name: str = ""
    description: str = ""
    parameters: dict = {}
    def execute(self, **kwargs) -> str
    def to_tool_spec(self) -> dict
```

### AgentLoop 驱动方式

```python
class AgentLoop:
    def __init__(self, skill_manager, memory, session, llm_client)
    def tick(self) -> list[dict]  # 由 QTimer 或 while 循环驱动
```
