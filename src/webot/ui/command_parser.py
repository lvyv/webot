import re


class CommandParser:
    def __init__(self):
        self._commands = []

    def register(self, name, pattern, handler):
        self._commands.append({
            "name": name,
            "pattern": re.compile(pattern),
            "handler": handler,
        })

    def execute(self, text):
        text = text.strip()
        for cmd in self._commands:
            m = cmd["pattern"].match(text)
            if m:
                cmd["handler"](*m.groups())
                return True
        return False
