import os
import tempfile

import cv2
import numpy as np
import pyautogui

from ..utils import (
    IMG_CHAT_HISTORY,
    PANEL_CHAT_HISTORY_TOP_OFFSET,
    CONFIDENCE_LEVEL,
)
from ..utils import get_logger
from .base import Skill
from .cursor_pos_calculate_skill import calculate_cursor_position
from .scroll_skill import scroll_repeatedly

logger = get_logger(__name__)



def compare_by_absdiff(img_path1, img_path2):
    img1 = cv2.imread(img_path1)
    img2 = cv2.imread(img_path2)
    if img1.shape != img2.shape:
        h, w = img1.shape[:2]
        img2 = cv2.resize(img2, (w, h))
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    diff = cv2.absdiff(gray1, gray2)
    _, thresh = cv2.threshold(diff, 10, 255, cv2.THRESH_BINARY)
    kernel = np.ones((5, 5), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    img_result = img1.copy()
    x_min, y_min = float('inf'), float('inf')
    x_max, y_max = float('-inf'), float('-inf')
    for contour in contours:
        if cv2.contourArea(contour) < 500:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        cv2.rectangle(img_result, (x, y), (x + w, y + h), (0, 0, 255), 1)
        x_min = min(x_min, x)
        y_min = min(y_min, y)
        x_max = max(x_max, x + w)
        y_max = max(y_max, y + h)
    if x_min != float('inf'):
        cv2.rectangle(img_result, (x_min, y_min), (x_max, y_max), (0, 0, 255), 1)
    return img_result, thresh, (x_min, y_min, x_max, y_max)


def capture_scroll_diff():
    result = calculate_cursor_position(IMG_CHAT_HISTORY, confidence=CONFIDENCE_LEVEL)
    if not result["found"]:
        logger.error("未找到聊天历史图标")
        return None

    icon_x, icon_y = result["x"], result["y"]
    pyautogui.moveTo(icon_x, icon_y + PANEL_CHAT_HISTORY_TOP_OFFSET)

    tmpdir = tempfile.gettempdir()
    before_path = os.path.join(tmpdir, "webot_before_scroll.png")
    after_path = os.path.join(tmpdir, "webot_after_scroll.png")

    try:
        pil_img = pyautogui.screenshot()
        pil_img.save(before_path)
        logger.info(f"滚动前截图已保存: {before_path}")
    except Exception as e:
        logger.error(f"截图失败: {e}")
        return None

    scroll_repeatedly(amount=30, times=1, direction="up")

    try:
        pil_img = pyautogui.screenshot()
        pil_img.save(after_path)
        logger.info(f"滚动后截图已保存: {after_path}")
    except Exception as e:
        logger.error(f"截图失败: {e}")
        return None

    diff_img, bin_img, rect = compare_by_absdiff(before_path, after_path)
    x_min, y_min, x_max, y_max = rect
    has_diff = x_min != float('inf')

    if has_diff:
        diff_path = os.path.join(tmpdir, "webot_scroll_diff.png")
        cv2.imwrite(diff_path, diff_img)
        logger.info(f"差异图已保存: {diff_path}, 区域 ({x_min},{y_min})-({x_max},{y_max})")
    else:
        logger.info("滚动前后无差异")

    cv2.imshow('Threshold Result', bin_img)
    cv2.waitKey(0)          # 等待按任意键关闭窗口
    cv2.destroyAllWindows()

    return {
        "has_diff": has_diff,
        "diff_rect": (int(x_min), int(y_min), int(x_max), int(y_max)) if has_diff else None,
        "before_path": before_path,
        "after_path": after_path,
    }


class CaptureScrollDiffSkill(Skill):
    name = "capture_scroll_diff"
    description = "在聊天历史面板中滚动一次，对比滚动前后的截图差异"
    parameters = {}

    def execute(self):
        result = capture_scroll_diff()
        if result is None:
            return "操作失败"
        if result["has_diff"]:
            return f"检测到内容变化，差异区域: {result['diff_rect']}"
        return "滚动前后无差异"
