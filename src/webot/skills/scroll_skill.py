# -*- coding: utf-8 -*-
# skills/scroll_skill.py

import pyautogui
import time
from ..utils import SCROLL_DELAY
from ..utils import get_logger
from .base import Skill

logger = get_logger(__name__)

def scroll_page(delta, duration=SCROLL_DELAY):
    pyautogui.scroll(delta)
    time.sleep(duration)
    logger.debug(f"滚动 {delta} 格")

def scroll_repeatedly(amount=30, times=1, direction="up"):
    # 1 times = 40 pixels per 30 amount.
    delta = amount if direction == "up" else -amount
    for _ in range(times):
        scroll_page(delta)
    logger.info(f"完成滚动: {direction} {amount} 格，共 {times} 次")


class ScrollRepeatedlySkill(Skill):
    name = "scroll_repeatedly"
    description = "反复滚动页面"
    parameters = {
        "amount": {"type": "integer", "description": "滚动量"},
        "times": {"type": "integer", "description": "滚动次数"},
        "direction": {"type": "string", "description": "方向 up/down"},
    }

    def execute(self, amount=30, times=1, direction="up"):
        scroll_repeatedly(amount=int(amount), times=int(times), direction=direction)
        return f"已滚动 {direction} {amount}x{times}"