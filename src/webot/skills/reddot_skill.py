import os
import tempfile

import cv2
import numpy as np
import pyautogui
import pygetwindow as gw

from ..config import (
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
)
from ..utils import get_logger
from .base import Skill

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
    list_w = int(cw * CHAT_LIST_WIDTH_RATIO)
    region = (
        left + CHAT_LIST_TAB_WIDTH,
        top + CHAT_LIST_TOP_OFFSET,
        list_w - CHAT_LIST_TAB_WIDTH,
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

# def detect_red_dots(bgr_img):
#     hsv = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2HSV)
#     mask1 = cv2.inRange(hsv, np.array([RED_DOT_HUE_LOW1, RED_DOT_SAT_MIN, RED_DOT_VAL_MIN]),
#                         np.array([RED_DOT_HUE_HIGH1, 255, 255]))
#     mask2 = cv2.inRange(hsv, np.array([RED_DOT_HUE_LOW2, RED_DOT_SAT_MIN, RED_DOT_VAL_MIN]),
#                         np.array([RED_DOT_HUE_HIGH2, 255, 255]))
#     mask = cv2.bitwise_or(mask1, mask2)
#     kernel = np.ones((3, 3), np.uint8)
#     mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

#     contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
#     dots = []
#     for c in contours:
#         area = cv2.contourArea(c)
#         if RED_DOT_AREA_MIN <= area <= RED_DOT_AREA_MAX or RED_DOT_AREA_MIN2 <= area <= RED_DOT_AREA_MAX2:
#             M = cv2.moments(c)
#             if M["m00"] != 0:
#                 cx = int(M["m10"] / M["m00"])
#                 cy = int(M["m01"] / M["m00"])
#                 dots.append((cx, cy, area))
#     return dots

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

def _infer_item_index(y):
    return y // CHAT_ITEM_HEIGHT


def ocr_chat_list(bgr_img):
    ocr = get_ocr_engine()
    # 注意：PaddleOCR 内部通常期望 RGB 格式，而 OpenCV 读取的是 BGR
    # 建议先转换颜色通道，避免识别结果偏色或准确率下降
    rgb_img = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
    result = ocr.predict(input=rgb_img)   # 直接传入 numpy 数组

    if not result:
        return []

    page = result[0]
    boxes = page.get("rec_boxes", [])
    texts = page.get("rec_texts", [])
    scores = page.get("rec_scores", [])

    items = []
    for box, text, score in zip(boxes, texts, scores):
        x1, y1, x2, y2 = box
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        idx = _infer_item_index(cy)
        if idx is not None:
            items.append({
                "text": text,
                "score": score,
                "box": box,
                "cx": cx,
                "cy": cy,
                "item_index": idx,
            })
    return items
    # ocr = get_ocr_engine()
    # tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    # tmp_path = tmp.name
    # tmp.close()
    # try:
    #     cv2.imwrite(tmp_path, bgr_img)
    #     result = ocr.predict(input=tmp_path)
    # finally:
    #     os.unlink(tmp_path)

    # if not result:
    #     return []

    # page = result[0]
    # boxes = page.get("rec_boxes", [])
    # texts = page.get("rec_texts", [])
    # scores = page.get("rec_scores", [])

    # items = []
    # for box, text, score in zip(boxes, texts, scores):
    #     x1, y1, x2, y2 = box
    #     cx = (x1 + x2) / 2
    #     cy = (y1 + y2) / 2
    #     idx = _infer_item_index(cy)
    #     if idx is not None:
    #         items.append({
    #             "text": text,
    #             "score": score,
    #             "box": box,
    #             "cx": cx,
    #             "cy": cy,
    #             "item_index": idx,
    #         })
    # return items


def group_items_by_chat(items):
    groups = {}
    for it in items:
        idx = it["item_index"]
        groups.setdefault(idx, []).append(it)

    sorted_groups = []
    for idx in sorted(groups.keys()):
        sorted_groups.append((idx, groups[idx]))
    return sorted_groups


# def match_red_dots_to_items(red_dots, sorted_groups):
#     red_by_idx = {}
#     for cx, cy, area in red_dots:
#         idx = _infer_item_index(cy)
#         if idx is not None:
#             red_by_idx.setdefault(idx, []).append((cx, cy, area))

#     result = []
#     for idx, items in sorted_groups:
#         name = ""
#         preview = ""
#         for it in items:
#             if not name:
#                 name = it["text"]
#             elif it["cy"] > items[0]["cy"] + 15:
#                 if not preview:
#                     preview = it["text"]
#         count = len(red_by_idx.get(idx, []))
#         if count > 0:
#             result.append({
#                 "chat_name": name,
#                 "preview": preview,
#                 "unread_count": count,
#                 "item_index": idx,
#             })
#     return result

def match_red_dots_to_items(red_dots, sorted_groups):
    # 收集所有红点坐标（只取前两个值）
    red_dot_points = [(x, y) for x, y, _ in red_dots]
    
    # 用于存储每个分组中匹配的项
    filtered_result = []
    
    for idx, items in sorted_groups:
        # 检查当前分组中的每个item
        matched_items = []
        preview = ''
        for it in items:
            # 获取box坐标 [x1, y1, x2, y2]
            box = it.get("box")
            if len(box) < 4:
                continue
            x1, y1, x2, y2 = box
            
            # 检查是否有任何红点落在该box内
            point_in_box = False
            for px, py in red_dot_points:
                if x1 <= px <= x2 and y1 <= py <= y2:
                    point_in_box = True
                    preview = f'(x = {px}, y = {py})'  # 记录第一个匹配的红点坐标作为预览（仅供调试）
                    break
            
            if point_in_box:
                matched_items.append(it)
        
        # 如果有匹配的item，才保留这个分组
        if matched_items:
            # 提取名称和预览（使用原逻辑）
            name = ""
            for it in matched_items:
                if not name:
                    name = it["text"]
                elif it.get("cy", 0) > matched_items[0].get("cy", 0) + 15:
                    if not preview:
                        preview = it["text"]
            
            # 计算该分组中匹配的红点数量
            count = 0
            for px, py in red_dot_points:
                for it in matched_items:
                    box = it.get("box")
                    if len(box) >= 4:
                        x1, y1, x2, y2 = box
                        if x1 <= px <= x2 and y1 <= py <= y2:
                            count += 1
                            break
            
            if count > 0:
                filtered_result.append({
                    "chat_name": name,
                    "preview": preview,
                    "unread_count": count,
                    "item_index": idx,
                })
    
    return filtered_result

def get_unread_chats():
    img = capture_chat_list_region() # 这个图片是微信窗口左边0，下90（让开搜索和我），0.3宽度的区域
    if img is None:
        return []

    dots = detect_red_dots(img)
    if not dots:
        logger.debug("未检测到红点")
        return []

    items = ocr_chat_list(img)
    if not items:
        logger.warning("聊天列表 OCR 未返回任何文本")
        return []

    groups = group_items_by_chat(items)
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
