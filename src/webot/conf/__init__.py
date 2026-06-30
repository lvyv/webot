import os

_conf_dir = os.path.dirname(os.path.abspath(__file__))
RULES_PATH = os.path.join(_conf_dir, "rules.json")

__all__ = ["RULES_PATH"]
