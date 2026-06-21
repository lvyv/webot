# -*- coding: utf-8 -*-
# skills/wait_skill.py

import time
from ..utils import get_logger
from .base import Skill

logger = get_logger(__name__)

def wait_for_user_focus(seconds=3, message="请切换到微信聊天窗口"):
    logger.info(f"{message}，{seconds} 秒后继续执行...")
    time.sleep(seconds)


class WaitForUserFocusSkill(Skill):
    name = "wait_for_user_focus"
    description = "等待用户切换到指定窗口"
    parameters = {
        "seconds": {"type": "integer", "description": "等待秒数"},
        "message": {"type": "string", "description": "提示信息"},
    }

    def execute(self, seconds=3, message="请切换到微信聊天窗口"):
        wait_for_user_focus(seconds=int(seconds), message=message)
        return f"等待 {seconds} 秒完成"