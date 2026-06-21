# -*- coding: utf-8 -*-
# skills/window_skill.py

import pyautogui
import pygetwindow as gw
import time
from ..utils import get_logger
from .base import Skill

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


def maximize_window(window_title):
    """
    最大化指定标题的窗口。

    Args:
        window_title (str): 窗口标题（支持模糊匹配）

    Returns:
        bool: 成功返回 True，失败返回 False
    """
    windows = gw.getWindowsWithTitle(window_title)
    if windows:
        win = windows[0]
        try:
            win.maximize()
            logger.info(f"窗口已最大化: {window_title}")
            return True
        except Exception as e:
            logger.error(f"最大化窗口失败: {window_title}, 错误: {e}")
            return False
    else:
        logger.error(f"最大化失败，未找到窗口: {window_title}")
        return False

def move_window(window_title, x, y):
    windows = gw.getWindowsWithTitle(window_title)
    if not windows:
        logger.error(f"未找到窗口: {window_title}")
        return False
    win = windows[0]
    win.moveTo(x, y)
    logger.info(f"窗口已移动: {window_title} -> ({x}, {y})")
    return True


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


class ActivateWindowSkill(Skill):
    name = "activate_window"
    description = "激活指定标题的窗口"
    parameters = {
        "window_title": {"type": "string", "description": "窗口标题"},
    }

    def execute(self, window_title):
        ok = activate_window(window_title)
        return f"窗口 {window_title} 已激活" if ok else f"激活失败"


class ResizeWindowSkill(Skill):
    name = "resize_window"
    description = "调整窗口大小"
    parameters = {
        "window_title": {"type": "string", "description": "窗口标题"},
        "width": {"type": "integer", "description": "宽度"},
        "height": {"type": "integer", "description": "高度"},
    }

    def execute(self, window_title, width, height):
        ok = resize_window(window_title, width, height)
        return f"窗口已调整 {width}x{height}" if ok else "调整失败"


class MoveWindowSkill(Skill):
    name = "move_window"
    description = "移动窗口到指定坐标"
    parameters = {
        "window_title": {"type": "string", "description": "窗口标题"},
        "x": {"type": "integer", "description": "X 坐标"},
        "y": {"type": "integer", "description": "Y 坐标"},
    }

    def execute(self, window_title, x, y):
        ok = move_window(window_title, x, y)
        return f"窗口已移动到 ({x}, {y})" if ok else "移动失败"