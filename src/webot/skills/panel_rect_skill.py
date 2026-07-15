import ctypes
import time
import pyautogui
import pygetwindow as gw

from webot.utils.utils import get_image_path
from ..utils import (
    CHAT_LIST_WIDTH_RATIO,
    CHAT_LIST_TOP_OFFSET,
    TITLE_BAR_HEIGHT,
    LEFT_TOOLBAR_WIDTH,
    CHAT_HISTORY_TOP_OFFSET,
    CHAT_INPUT_HEIGHT,
    RIGHT_PANEL_RIGHT_MARGIN,
)
from ..utils import get_logger
from ..utils import config

logger = get_logger(__name__)

def _calculate_screen_position(image_path, confidence=config.CONFIDENCE_LEVEL, region=None):
    try:
        location = pyautogui.locateCenterOnScreen(
            image=get_image_path(image_path),
            confidence=confidence,
            region=region,
        )
        if location:
            logger.info(f"定位成功: {image_path} -> ({location.x}, {location.y})")
            return {"x": location.x, "y": location.y, "found": True}
    except Exception as e:
        logger.error(f"定位出错: {e}")
    return None

def _get_window_dims(title=config.WECHAT_WINDOW_TITLE, classname=config.WECHAT_WINDOW_CLSNAME, delay=config.RETRY_DELAY):
    """获取微信窗口的矩形位置和大小"""
    windows = gw.getWindowsWithTitle(title)
    if not windows:
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(classname, None)
        if not hwnd:
            logger.warning("未找到微信窗口")
            return False
    else:
        hwnd = windows[0]._hWnd
    rect = ctypes.wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    time.sleep(delay)  # 等待窗口激活
    return {
        "left": rect.left,
        "top": rect.top,
        "right": rect.right,
        "bottom": rect.bottom,
        "w": rect.right - rect.left,
        "h": rect.bottom - rect.top,
    }


def get_title_bar_rect():
    win = _get_window_dims()
    pt = _calculate_screen_position(config.IMG_CLOSE_BUTTON)
    if win is None or pt is None:
        return None
    if pt["found"]:
        height = int(pt["y"]) - win["top"] +  10 # 关闭按钮的中心点到标题栏底部的距离大约是标题栏高度的一半
    else:
        height = TITLE_BAR_HEIGHT
    return (win["left"], win["top"], win["w"], height)


def get_left_toolbar_rect():
    win = _get_window_dims()
    if win is None:
        return None
    y = win["top"] + config.CHAT_LIST_TOP_OFFSET
    return (win["left"], y, config.CHAT_LIST_LEFT_OFFSET, win["h"] - config.CHAT_LIST_TOP_OFFSET)


def get_search_bar_rect():
    win = _get_window_dims()
    ptR = _calculate_screen_position(config.IMG_SHORTCUTS)
    
    if win is None:
        return None
    # list_w = int(win["w"] * CHAT_LIST_WIDTH_RATIO)
    x = win["left"] + config.CHAT_LIST_LEFT_OFFSET
    y = win["top"] + config.TITLE_BAR_HEIGHT
    w = ptR["x"] - win["left"]- config.CHAT_LIST_LEFT_OFFSET + config.SHORTCUTS_CENTER_TO_LIST_RIGHT
    h = config.CHAT_LIST_TOP_OFFSET - config.TITLE_BAR_HEIGHT
    return (int(x), int(y), int(w), int(h))


def get_contact_list_rect():
    win = _get_window_dims()
    ptR = _calculate_screen_position(config.IMG_SHORTCUTS)
    if win is None:
        return None
    x = win["left"] + LEFT_TOOLBAR_WIDTH
    y = win["top"] + CHAT_LIST_TOP_OFFSET
    w = ptR["x"] - win["left"]- config.CHAT_LIST_LEFT_OFFSET + config.SHORTCUTS_CENTER_TO_LIST_RIGHT
    h = win["h"] - CHAT_LIST_TOP_OFFSET
    return (int(x), int(y), int(w), int(h))


def get_chat_history_rect():
    win = _get_window_dims()
    ptR = _calculate_screen_position(config.IMG_SHORTCUTS)
    ptRD = _calculate_screen_position(config.IMG_MSG_INPUT_RIGHT_UP_CORNER)
    list_w = ptR["x"] - win["left"] - config.CHAT_LIST_LEFT_OFFSET + config.SHORTCUTS_CENTER_TO_LIST_RIGHT
    if win is None:
        return None
    x = win["left"] + list_w + config.CHAT_LIST_LEFT_OFFSET
    y = win["top"] + config.PANEL_CHAT_HISTORY_TOP_OFFSET
    w = win["w"] - list_w -config.CHAT_LIST_LEFT_OFFSET
    h = ptRD['y'] - y 
    return (int(x), int(y), int(w), int(h))


def get_message_input_rect():
    win = _get_window_dims()
    ptR = _calculate_screen_position(config.IMG_MSG_INPUT_RIGHT_UP_CORNER)
    ptR2 = _calculate_screen_position(config.IMG_SHORTCUTS)
    list_w = ptR2["x"] - win["left"] - config.CHAT_LIST_LEFT_OFFSET + config.SHORTCUTS_CENTER_TO_LIST_RIGHT
    if win is None or ptR is None:
        return None
    x = win["left"] + list_w + config.CHAT_LIST_LEFT_OFFSET
    y = ptR['y'] - 5
    w = win["w"] - list_w -config.CHAT_LIST_LEFT_OFFSET
    h = win['top'] + win["h"] - y
    return (int(x), int(y), int(w), int(h))
