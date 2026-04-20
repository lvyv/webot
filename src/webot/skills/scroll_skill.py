# -*- coding: utf-8 -*-
# skills/scroll_skill.py

import pyautogui
import time
from ..config import SCROLL_DELAY
from ..utils import get_logger

logger = get_logger(__name__)

def scroll_page(delta, duration=SCROLL_DELAY):
    pyautogui.scroll(delta)
    time.sleep(duration)
    logger.debug(f"滚动 {delta} 格")

def scroll_repeatedly(amount, times=1, direction="up"):
    delta = amount if direction == "up" else -amount
    for _ in range(times):
        scroll_page(delta)
    logger.info(f"完成滚动: {direction} {amount} 格，共 {times} 次")