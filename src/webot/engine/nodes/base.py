from abc import ABC, abstractmethod


class RuleNode(ABC):
    name: str = ""

    @abstractmethod
    def execute(self, ctx: dict) -> dict:
        """
        执行节点逻辑。
        ctx: 共享上下文（消息内容、中间结果等）
        返回: {"next": "下一节点ID" | None, "output": ..., ...}
        """
