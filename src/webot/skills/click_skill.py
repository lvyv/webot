# -*- coding: utf-8 -*-
# skills/click_skill.py

import pyautogui
import time
import os
from ..config import RETRY_TIMES, RETRY_DELAY, CONFIDENCE_LEVEL
from ..utils import get_logger, get_image_path
from .base import Skill

logger = get_logger(__name__)

def click_ui_element(image_path, confidence=CONFIDENCE_LEVEL,
                     retry=RETRY_TIMES, delay=RETRY_DELAY):
    for attempt in range(1, retry + 1):
        try:
            location = pyautogui.locateCenterOnScreen(
                image=image_path, confidence=confidence
            )
            if location:
                pyautogui.click(location)
                logger.info(f"点击成功:{location.x} {location.y}  {os.path.basename(image_path)}")
                return True
            else:
                logger.warning(f"尝试 {attempt}/{retry} 未找到: {image_path}")
                time.sleep(delay)
        except Exception as e:
            logger.error(f"查找/点击出错: {e}")
            time.sleep(delay)
    logger.error(f"最终失败，无法点击: {image_path}")
    return False


class ClickUiElementSkill(Skill):
    name = "click_ui_element"
    description = "查找并点击屏幕上的目标图标"
    parameters = {
        "image_path": {"type": "string", "description": "图标文件名，如 contacts.png"},
    }

    def execute(self, image_path):
        ok = click_ui_element(get_image_path(image_path))
        return f"已点击 {image_path}" if ok else f"点击 {image_path} 失败"