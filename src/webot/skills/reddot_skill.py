import os
import tempfile

import cv2
import numpy as np
import pyautogui
import pygetwindow as gw

from ..utils import (
    WECHAT_WINDOW_TITLE,
    CHAT_LIST_WIDTH_RATIO,
    CHAT_ITEM_HEIGHT,
    CHAT_LIST_TOP_OFFSET,
    CHAT_LIST_TAB_WIDTH,
    RED_DOT_SAT_MIN,
    RED_DOT_VAL_MIN,
    RED_DOT_AREA_MIN,
    RED_DOT_AREA_MAX,
    RED_DOT_AREA_MIN2,
    RED_DOT_AREA_MAX2,
    RED_DOT_OFFSET_X,
    RED_DOT_OFFSET_Y,
    RED_DOT_HUE_LOW1,
    RED_DOT_HUE_HIGH1,
    RED_DOT_HUE_LOW2,
    RED_DOT_HUE_HIGH2,
    OCR_CONFIDENCE_THRESHOLD,
    IMG_SHORTCUTS,
    SHORTCUTS_CENTER_TO_LIST_RIGHT,
    CONFIDENCE_LEVEL,
)
from ..utils import get_logger
from .base import Skill
from .cursor_pos_calculate_skill import calculate_cursor_position

logger = get_logger(__name__)


_ocr_engine = None


def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        from paddleocr import PaddleOCR
        _ocr_engine = PaddleOCR(use_doc_unwarping=False)
    return _ocr_engine


def get_wechat_rect():
    windows = gw.getWindowsWithTitle(WECHAT_WINDOW_TITLE)
    if not windows:
        logger.error(f"未找到窗口: {WECHAT_WINDOW_TITLE}")
        return None
    win = windows[0]
    if win.isMinimized:
        logger.warning("微信窗口已最小化")
        return None
    return (win.left, win.top, win.right, win.bottom)


def capture_chat_list_region():
    rect = get_wechat_rect()
    if rect is None:
        return None

    left, top, right, bottom = rect
    cw = right - left
    ch = bottom - top

    # 用 shortcuts 按钮动态计算聊天列表右边界
    list_right = None
    result = calculate_cursor_position(IMG_SHORTCUTS, confidence=CONFIDENCE_LEVEL)
    if result["found"]:
        button_cx = result["x"]
        list_right = int(button_cx) + SHORTCUTS_CENTER_TO_LIST_RIGHT
        logger.info(f"shortcuts 按钮中心 x={button_cx}, 列表右边界={list_right}")
    else:
        logger.warning("shortcuts 按钮未找到，使用固定比例")

    if list_right is None:
        list_w = int(cw * CHAT_LIST_WIDTH_RATIO)
        list_right = left + list_w

    region = (
        left + CHAT_LIST_TAB_WIDTH,
        top + CHAT_LIST_TOP_OFFSET,
        list_right - (left + CHAT_LIST_TAB_WIDTH),
        ch - CHAT_LIST_TOP_OFFSET,
    )

    try:
        pil_img = pyautogui.screenshot(region=region)
    except OSError:
        logger.error("截图失败：可能微信窗口被遮挡或不在屏幕上")
        return None

    bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    # debug_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..\..", "screenshots", "chat_list_debug.png")
    # cv2.imwrite(debug_path, bgr)
    # logger.info(f"聊天列表截图已保存: {debug_path}")

    return bgr

def detect_red_dots(bgr_img, draw_result=False):
    hsv = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, np.array([RED_DOT_HUE_LOW1, RED_DOT_SAT_MIN, RED_DOT_VAL_MIN]),
                        np.array([RED_DOT_HUE_HIGH1, 255, 255]))
    mask2 = cv2.inRange(hsv, np.array([RED_DOT_HUE_LOW2, RED_DOT_SAT_MIN, RED_DOT_VAL_MIN]),
                        np.array([RED_DOT_HUE_HIGH2, 255, 255]))
    mask = cv2.bitwise_or(mask1, mask2)
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    dots = []
    for c in contours:
        area = cv2.contourArea(c)
        if RED_DOT_AREA_MIN <= area <= RED_DOT_AREA_MAX or RED_DOT_AREA_MIN2 <= area <= RED_DOT_AREA_MAX2:
            M = cv2.moments(c)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                dots.append((cx + RED_DOT_OFFSET_X, cy + RED_DOT_OFFSET_Y, area))
    
    # ===== 新增：绘制检测结果 =====
    if draw_result and len(dots) > 0:
        # 复制原图，避免修改原始图像
        result_img = bgr_img.copy()
        
        # 绘制每个检测到的红点
        for i, (cx, cy, area) in enumerate(dots):
            # 1. 绘制红色圆圈标记红点位置（半径根据面积动态调整）
            radius = int(np.sqrt(area / np.pi))  # 从面积估算半径
            cv2.circle(result_img, (cx, cy), radius, (0, 255, 0), 2)  # 绿色圆圈
            
            # 2. 在圆心画一个十字准星
            cross_size = 8
            cv2.drawMarker(result_img, (cx, cy), (0, 255, 255), 
                          cv2.MARKER_CROSS, cross_size, 2)
            
            # 3. 标注序号和面积信息
            label = f"#{i+1} area:{area:.0f}"
            cv2.putText(result_img, label, (cx + 15, cy ),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 100, 100), 1)
        
        # 显示结果
        cv2.imshow('Detected Red Dots', result_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        
        # 可选：保存结果图片
        # cv2.imwrite('detected_result.png', result_img)
    
    return dots

def ocr_chat_list(bgr_img):
    ocr = get_ocr_engine()
    rgb_img = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
    result = ocr.predict(input=rgb_img)

    if not result:
        return []

    page = result[0]
    boxes = page.get("rec_boxes", [])
    texts = page.get("rec_texts", [])
    scores = page.get("rec_scores", [])

    items = []
    for box, text, score in zip(boxes, texts, scores):
        if score < OCR_CONFIDENCE_THRESHOLD:
            continue
        x1, y1, x2, y2 = box
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        items.append({
            "text": text,
            "score": score,
            "box": box,
            "cx": cx,
            "cy": cy,
        })
    return items


def group_items_by_chat(items):
    if not items:
        return []
    sorted_items = sorted(items, key=lambda x: x["cy"])
    groups = []
    current = [sorted_items[0]]
    for it in sorted_items[1:]:
        if it["cy"] - current[-1]["cy"] < CHAT_ITEM_HEIGHT:
            current.append(it)
        else:
            groups.append(current)
            current = [it]
    if current:
        groups.append(current)
    return list(enumerate(groups))

def match_red_dots_to_items(red_dots, sorted_groups):
    red_dot_points = [(x, y) for x, y, _ in red_dots]
    result = []

    for idx, group in sorted_groups:
        sorted_items = sorted(group, key=lambda x: x["cy"])
        # 找到第一个被红点命中的文字块（按从上到下顺序）
        name = None
        position = None
        hit_index = -1
        for i, it in enumerate(sorted_items):
            box = it.get("box")
            if len(box) < 4:
                continue
            x1, y1, x2, y2 = box
            for px, py in red_dot_points:
                if x1 <= px <= x2 and y1 <= py <= y2:
                    name = it["text"]
                    position = {"x": px, "y": py}
                    hit_index = i
                    break
            if name is not None:
                break

        if name is None:
            continue

        # 被命中文字块的下一个文字块作为时间
        time = ""
        if hit_index + 1 < len(sorted_items):
            time = sorted_items[hit_index + 1]["text"]
        # 被命中文字块的下两个文字块作为时间
        preview = ""
        if hit_index + 2 < len(sorted_items):
            preview = sorted_items[hit_index + 2]["text"]

        result.append({
            "chat_name": name,
            "time": time,
            "preview": preview,
            "item_index": idx,
            "position": position,
        })

    return result

def get_unread_chats():
    img = capture_chat_list_region()    # 这个区域是图片是微信窗口左边0，并通过识别微信联系人面板上面的搜索框右侧"+"图标位置计算得到。
    if img is None:
        return []

    dots = detect_red_dots(img)         # 这个红点返回值是向右下偏移了RED_DOT_OFFSET_X (Y)的位置
    if not dots:
        logger.debug("未检测到红点")
        return []

    items = ocr_chat_list(img)          # 联系人面板内所有文字识别结果
    if not items:
        logger.warning("聊天列表 OCR 未返回任何文本")
        return []

    groups = group_items_by_chat(items) # 按照每个识别文字块纵向距离进行分组，这样每个组就是一个聊天联系人，包含姓名、时间、预览
    matched = match_red_dots_to_items(dots, groups)
    if matched:
        names = [m["chat_name"] for m in matched]
        logger.info(f"检测到未读: {names}")
    return matched


class GetUnreadChatsSkill(Skill):
    name = "get_unread_chats"
    description = "检测微信未读消息（红点）"
    parameters = {}

    def execute(self):
        unreads = get_unread_chats()
        if not unreads:
            return "没有未读消息"
        lines = [f"{m['chat_name']}: {m.get('preview','')}" for m in unreads]
        return "\n".join(lines)
