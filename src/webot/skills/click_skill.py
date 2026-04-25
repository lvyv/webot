# -*- coding: utf-8 -*-
# skills/click_skill.py

import pyautogui
import time
import os
from ..config import RETRY_TIMES, RETRY_DELAY, CONFIDENCE_LEVEL
from ..utils import get_logger

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