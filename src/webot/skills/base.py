from ..utils import get_logger

logger = get_logger(__name__)


class Skill:
    name = ""
    description = ""
    parameters = {}

    def execute(self, **kwargs):
        raise NotImplementedError

    def to_tool_spec(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": list(self.parameters.keys()),
                },
            },
        }
