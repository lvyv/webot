from ..utils import get_logger

logger = get_logger(__name__)


class Session:
    def __init__(self):
        self._contexts: dict[str, list[dict]] = {}

    def add_message(self, chat_name, role, content, tool_calls=None):
        if chat_name not in self._contexts:
            self._contexts[chat_name] = []
        msg = {"role": role, "content": content}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self._contexts[chat_name].append(msg)

    def get_context(self, chat_name):
        return self._contexts.get(chat_name, [])

    def set_context(self, chat_name, messages):
        self._contexts[chat_name] = list(messages)

    def pop_oldest(self, chat_name, max_len=20):
        ctx = self._contexts.get(chat_name, [])
        while len(ctx) > max_len:
            ctx.pop(0)

    def is_new(self, chat_name, preview):
        ctx = self._contexts.get(chat_name, [])
        if not ctx:
            return True
        last = ctx[-1].get("content", "")
        if not last or not preview:
            return True
        return last != preview

    def clear(self, chat_name=None):
        if chat_name:
            self._contexts.pop(chat_name, None)
        else:
            self._contexts.clear()
