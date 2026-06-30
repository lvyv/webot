# ---------- 声明需要的 user32 函数 ----------
# import logging
# import ctypes
# from ctypes import wintypes
# import pygetwindow as gw
# import time

# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
#     datefmt='%Y-%m-%d %H:%M:%S'
# )
# logger = logging.getLogger()
# logger.setLevel(logging.INFO)
# # 加载 user32.dll

# import ctypes
# from ctypes import wintypes
# import time

# user32 = ctypes.windll.user32

# # ---------- 常量 ----------
# SW_RESTORE = 9
# SW_SHOWMAXIMIZED = 3
# MOUSEEVENTF_LEFTDOWN = 0x0002
# MOUSEEVENTF_LEFTUP   = 0x0004
# WM_NCLBUTTONDOWN = 0x00A1
# WM_NCLBUTTONDBLCLK = 0x00A3
# HT_CAPTION = 0x0002   # 标题栏区域
# SM_CYCAPTION = 4
# # 使用 wintypes.RECT
# RECT = wintypes.RECT

# # ---------- 声明 API ----------
# user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
# user32.FindWindowW.restype  = wintypes.HWND

# user32.IsIconic.argtypes = [wintypes.HWND]
# user32.IsIconic.restype  = ctypes.c_bool

# user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
# user32.ShowWindow.restype  = ctypes.c_bool

# user32.SetForegroundWindow.argtypes = [wintypes.HWND]
# user32.SetForegroundWindow.restype  = ctypes.c_bool

# user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
# user32.GetWindowRect.restype  = ctypes.c_bool

# user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
# user32.SetCursorPos.restype  = ctypes.c_bool

# user32.mouse_event.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.ULONG]
# user32.mouse_event.restype  = None

# def double_click_titlebar_by_message(hwnd):
#     """通过真实鼠标双击标题栏（物理移动鼠标）"""
#     rect = wintypes.RECT()
#     if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
#         return False
#     # 计算标题栏高度
#     caption_height = user32.GetSystemMetrics(SM_CYCAPTION)
#     if caption_height == 0:
#         caption_height = 30  # 备用值
    
#     # 标题栏中心点
#     x = (rect.left + rect.right) // 2
#     y = rect.top + caption_height // 2

#     # 移动鼠标到目标位置
#     user32.SetCursorPos(x, y)
    
#     # 发送第一次点击（按下+弹起）
#     user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
#     user32.mouse_event(MOUSEEVENTF_LEFTUP,   0, 0, 0, 0)
    
#     # 双击间隔（Windows 默认约 200-500ms，这里给短一点 100ms 足以）
#     time.sleep(0.1)
    
#     # 发送第二次点击
#     user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
#     user32.mouse_event(MOUSEEVENTF_LEFTUP,   0, 0, 0, 0)
    
#     return True

# def activate_wechat(window_title=None, class_name="WeChatMainWndForPC"):
#     """
#     激活微信窗口（纯 ctypes，无 pygetwindow）。
#     如果 window_title 不为空，会尝试先用标题查找，否则用类名。
#     但建议直接使用类名。
#     """
#     try:
#         hwnd = None
#         # 1. 优先使用类名查找（微信固定类名）
#         if class_name:
#             hwnd = user32.FindWindowW(class_name, None)
#         # 2. 如果未找到且提供了标题，则用标题（通过 FindWindowW 同时指定标题和类名）
#         if not hwnd and window_title:
#             # 尝试用类名+标题查找
#             hwnd = user32.FindWindowW(class_name, window_title) if class_name else user32.FindWindowW(None, window_title)

#         if not hwnd:
#             logger.warning("未找到微信窗口")
#             return False

#         # 3. 如果窗口最小化则还原（也可使用最大化 SW_SHOWMAXIMIZED）
#         if user32.IsIconic(hwnd):
#             user32.ShowWindow(hwnd, SW_RESTORE)   # 或 SW_SHOWMAXIMIZED 直接最大化
#             time.sleep(0.2)

#         # 4. 窗口置前
#         user32.SetForegroundWindow(hwnd)
#         user32.ShowWindow(hwnd, SW_SHOWMAXIMIZED)
#         user32.SetForegroundWindow(hwnd)
#         user32.BringWindowToTop(hwnd)
#         time.sleep(0.1)
        
#         # 5. 双击标题栏，触发自绘刷新（微信窗口可能需要此操作）
#         double_click_titlebar_by_message(hwnd)  # 双击标题栏，触发自绘刷新
#         logger.info("微信已激活并刷新")
#         return True

#     except Exception as e:
#         logger.error(f"激活微信失败: {e}")
#         return False
    
# if __name__ == "__main__":
#     # 测试激活微信窗口
#     window_title = "微信"
#     class_name = "Qt51514QWindowIcon"
#     success = activate_wechat(window_title, class_name)
#     if success:
#         print("微信窗口已激活")
#     else:
#         print("未能激活微信窗口")

import pyautogui
from webot.skills.window_skill import activate_window
from webot.skills.scroll_skill import scroll_repeatedly
from webot.skills.cursor_pos_calculate_skill import calculate_cursor_position
from webot import config
from webot.utils import get_logger, get_image_path

logger = get_logger(__name__)

def locate_and_move_cursor(image_name, confidence=config.CONFIDENCE_LEVEL, xoffset=0, yoffset=50):
    result = calculate_cursor_position(image_name, confidence=confidence)
    if result["found"]:
        pyautogui.moveTo(result["x"] + xoffset, result["y"] + yoffset)
        logger.info(f"已定位并移动到 {image_name} -> ({result['x'] + xoffset}, {result['y'] + yoffset})")
        return True
    else:
        logger.warning(f"未找到 {image_name}")
        return False


def scroll_wechat(direction="down", amount=30, times=10):
    # activate_window(config.WECHAT_WINDOW_TITLE, config.WECHAT_WINDOW_CLSNAME)
    scroll_repeatedly(amount=amount, times=times, direction=direction)
    logger.info(f"微信窗口已滚动 {direction} {amount}x{times}")


if __name__ == "__main__":
    # 测试激活微信窗口
    # 1.滚动;2.抓图;3.截图t_diff_pic;
    window_title = "微信"
    class_name = "Qt51514QWindowIcon"
    success = activate_window(config.WECHAT_WINDOW_TITLE, config.WECHAT_WINDOW_CLSNAME)
    if success:
        logger.info("微信窗口已激活")
    else:
        logger.warning("未能激活微信窗口")
    if(locate_and_move_cursor(get_image_path(config.IMG_IMAGE), confidence=config.CONFIDENCE_LEVEL)):
    # 测试滚动微信窗口
        scroll_wechat(direction="down", amount=30, times=10)   