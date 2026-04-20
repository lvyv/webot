# -*- coding: utf-8 -*-
# skills/window_skill.py

import pyautogui
import pygetwindow as gw
import time
from ..utils import get_logger

logger = get_logger(__name__)

def activate_window(window_title):
    windows = gw.getWindowsWithTitle(window_title)
    if not windows:
        logger.error(f"未找到窗口: {window_title}")
        return False
    win = windows[0]
    if not win.isActive:
        win.activate()
    time.sleep(0.3)
    logger.info(f"窗口已激活: {window_title}")
    return True

def resize_window(window_title, width, height):
    windows = gw.getWindowsWithTitle(window_title)
    if windows:
        win = windows[0]
        win.resizeTo(width, height)
        logger.info(f"窗口已调整: {window_title} -> {width}x{height}")
        return True
    logger.error(f"调整大小失败，未找到窗口: {window_title}")
    return False

def center_window(window_title):
    windows = gw.getWindowsWithTitle(window_title)
    if not windows:
        logger.error(f"未找到窗口: {window_title}")
        return False
    win = windows[0]
    screen_w, screen_h = pyautogui.size()
    x = (screen_w - win.width) // 2
    y = (screen_h - win.height) // 2
    win.moveTo(x, y)
    logger.info(f"窗口已居中: {window_title}")
    return True