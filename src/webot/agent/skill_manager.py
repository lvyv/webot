from ..utils import get_logger

logger = get_logger(__name__)


class SkillManager:
    def __init__(self):
        self._skills = {}

    def register(self, skill):
        self._skills[skill.name] = skill
        logger.info(f"注册 skill: {skill.name}")

    def get_tools_spec(self):
        return [s.to_tool_spec() for s in self._skills.values()]

    def execute(self, name, args):
        skill = self._skills.get(name)
        if skill is None:
            logger.error(f"未找到 skill: {name}")
            return f"错误: 未知的 skill '{name}'"
        try:
            logger.info(f"执行 skill: {name}({args})")
            return skill.execute(**args)
        except Exception as e:
            logger.error(f"skill {name} 执行失败: {e}")
            return f"错误: skill '{name}' 执行失败 - {e}"
