# -*- coding: utf-8 -*-
# skills/input_skill.py

import pyautogui
import pyperclip
import time
from ..config import POST_CLICK_DELAY, PASTE_DELAY, CONFIDENCE_LEVEL
from ..utils import get_logger
from .click_skill import click_ui_element

logger = get_logger(__name__)

def input_text(text, press_enter=False):
    pyperclip.copy(text)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(PASTE_DELAY)
    if press_enter:
        pyautogui.press('enter')
    logger.info(f"已输入: {text[:30]}{'...' if len(text) > 30 else ''}")

def clear_text_field(image_path, confidence=None):
    if not click_ui_element(image_path, confidence=CONFIDENCE_LEVEL):
        logger.warning(f'无法找到文件：{image_path}')
        return False
    pyautogui.hotkey('ctrl', 'a')
    # 添加短暂延迟，确保操作被系统响应
    time.sleep(0.1)
    pyautogui.press('delete')
    return True

def find_and_input_text(image_path, text, send_enter=True, confidence=CONFIDENCE_LEVEL):
    if not click_ui_element(image_path, confidence=confidence):
        return False
    time.sleep(POST_CLICK_DELAY)
    input_text(text, press_enter=send_enter)
    return True