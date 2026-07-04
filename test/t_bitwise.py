#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 楚雄师范学院人工智能专业《自然语言处理》
# 微信Agent项目 PBL示例
# 主要解决微信界面面板元素的提取，以方便pyautogui库的操作，还可以通过深度学习的模型训练，这个应该更加靠谱，但暂时还没有人做。
#   1.标题栏，左侧边工具栏，
#   2.
# 用到opencv
#
# Awen. 2026.7
#
# 致谢
#
# Copyright (C) 2025 Awen <lvyu@cxtc.edu.cn>
# Licensed under the GNU LGPL v2.1 - https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html

"""
Run with:
    python ./t_bitwise.py
"""
import os
import sys
import cv2
import numpy as np
import pygetwindow as gw
import pyautogui
from PIL import ImageDraw

from webot.skills.scroll_diff_skill import capture_scroll_diff
from webot.skills.cursor_pos_calculate_skill import calculate_cursor_position
from webot.skills.panel_rect_skill import get_title_bar_rect, get_left_toolbar_rect, get_search_bar_rect, get_contact_list_rect, get_chat_history_rect, get_message_input_rect

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

def segment_chat_robust(img_path, min_area=500, photo_area_thresh=3000):
    """
    针对微信聊天记录，结合颜色和纹理分离背景与前景（气泡+文字+图片）
    返回：带矩形框的结果图、精细前景掩膜、矩形坐标列表
    """
    img = cv2.imread(img_path)
    if img is None:
        raise FileNotFoundError(f"图片未找到: {img_path}")
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # ========== 第一步：基于颜色的背景提取 ==========
    # 自动判断深浅色模式（取四角亮度）
    # corners = np.mean(gray[0:10, 0:10]) + np.mean(gray[0:10, w-10:w]) + \
    #           np.mean(gray[h-10:h, 0:10]) + np.mean(gray[h-10:h, w-10:w])
    # avg_bright = corners / 4

    hist = np.bincount(gray.flatten(), minlength=256)
    avg_bright = np.argmax(hist)

    if avg_bright > 127:  # 浅色模式（背景接近白色）
        lower_bg = np.array([0, 0, 180])
        upper_bg = np.array([180, 30, 255])
    else:                 # 深色模式（背景接近黑色）
        lower_bg = np.array([0, 0, 0])
        upper_bg = np.array([180, 255, 80])

    mask_bg_color = cv2.inRange(hsv, lower_bg, upper_bg)
    mask_fg_color = cv2.bitwise_not(mask_bg_color)  # 基于颜色的前景

    # ========== 第二步：基于纹理（梯度）提取照片区域 ==========
    # 计算图像梯度幅值（边缘强度）
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    magnitude = np.sqrt(sobelx**2 + sobely**2)
    magnitude = np.uint8(255 * magnitude / (np.max(magnitude) + 1e-6))
    
    # 梯度阈值（低于此值的视为平滑背景，高于此值的视为纹理/边缘）
    _, mask_grad = cv2.threshold(magnitude, 25, 255, cv2.THRESH_BINARY)

    # 大核闭运算：将照片内分散的边缘连接成完整的封闭区域
    kernel_big = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (30, 30))
    mask_grad_closed = cv2.morphologyEx(mask_grad, cv2.MORPH_CLOSE, kernel_big, iterations=1)

    # 提取较大的纹理块（过滤掉文字引起的小噪点，只保留照片区域）
    contours_grad, _ = cv2.findContours(mask_grad_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    mask_photo = np.zeros_like(mask_grad_closed)
    for cnt in contours_grad:
        if cv2.contourArea(cnt) > photo_area_thresh:  # 面积大于阈值才认为是照片
            cv2.drawContours(mask_photo, [cnt], -1, 255, -1)

    # ========== 第三步：融合颜色前景 + 纹理照片区域 ==========
    mask_fg_combined = cv2.bitwise_or(mask_fg_color, mask_photo)

    # ========== 第四步：形态学精细调整 ==========
    kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    # 开运算：去除孤立的小噪点（如屏幕上的灰尘或文字笔画断点）
    mask_fg_combined = cv2.morphologyEx(mask_fg_combined, cv2.MORPH_OPEN, kernel_small, iterations=1)
    # 闭运算：填充前景内部的细小空洞（如照片中的纯白/纯黑区域）
    mask_fg_combined = cv2.morphologyEx(mask_fg_combined, cv2.MORPH_CLOSE, kernel_small, iterations=2)

    # ========== 第五步：提取连通域并绘制矩形框 ==========
    contours, _ = cv2.findContours(mask_fg_combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    img_result = img.copy()
    rects = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:  # 过滤极小的噪点
            continue
        x, y, w_box, h_box = cv2.boundingRect(cnt)
        rects.append((x, y, x + w_box, y + h_box))
        cv2.rectangle(img_result, (x, y), (x + w_box, y + h_box), (0, 0, 255), 2)

    return img_result, mask_fg_combined, rects

def segment_and_box_chat(img_path, min_area=500, merge_distance=10):
    """
    读取聊天截图，分离前景（气泡+文字），并对每个连通区域绘制矩形框。
    返回：带矩形框的结果图、前景掩膜、矩形坐标列表。
    """
    img = cv2.imread(img_path)
    if img is None:
        raise FileNotFoundError(f"图片未找到: {img_path}")
    h, w = img.shape[:2]

    # 1. 转换为HSV，方便颜色阈值
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # 2. 自动判断深浅色模式（取四角平均亮度）
    corners = np.mean(img[0:10, 0:10]) + np.mean(img[0:10, w-10:w]) + \
              np.mean(img[h-10:h, 0:10]) + np.mean(img[h-10:h, w-10:w])
    avg_bright = corners / 4

    if avg_bright > 127:  # 浅色模式
        lower_bg = np.array([0, 0, 180])
        upper_bg = np.array([180, 30, 255])
    else:                 # 深色模式
        lower_bg = np.array([0, 0, 0])
        upper_bg = np.array([180, 255, 80])

    # 3. 提取背景掩膜 → 取反得到前景掩膜
    mask_bg = cv2.inRange(hsv, lower_bg, upper_bg)
    mask_fg = cv2.bitwise_not(mask_bg)

    # 4. 形态学精修（填充气泡内文字空洞，去除零星噪点）
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask_fg = cv2.morphologyEx(mask_fg, cv2.MORPH_CLOSE, kernel, iterations=1)
    mask_fg = cv2.morphologyEx(mask_fg, cv2.MORPH_OPEN, kernel, iterations=1)

    # 5. 提取所有外轮廓（每个连通域）
    contours, _ = cv2.findContours(mask_fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 6. 对每个轮廓计算矩形框，过滤小面积
    rects = []
    img_result = img.copy()
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        x, y, w_box, h_box = cv2.boundingRect(cnt)
        rects.append((x, y, x + w_box, y + h_box))  # 保存 (x1, y1, x2, y2)
        cv2.rectangle(img_result, (x, y), (x + w_box, y + h_box), (0, 0, 255), 2)  # 红色框，线宽2

    # (可选) 合并距离较近的矩形（避免一个气泡被切成多个框，通常不需要）
    # 如果你想要合并，可以取消注释下面的 merge_rects 函数调用

    return img_result, mask_fg, rects

# 合并邻近矩形的辅助函数（如果需要）
def merge_rects(rects, distance=10):
    """
    将相互距离小于 distance 的矩形合并为一个大的矩形。
    rects: 列表，每个元素为 (x1, y1, x2, y2)
    """
    if not rects:
        return []
    merged = []
    # 简单贪心合并，实际可优化
    rects = sorted(rects, key=lambda r: (r[1], r[0]))  # 按y排序
    current = rects[0]
    for r in rects[1:]:
        # 检查是否在水平或垂直方向距离很近
        if (r[0] - current[2] < distance or current[0] - r[2] < distance) and \
           (r[1] - current[3] < distance or current[1] - r[3] < distance):
            # 合并
            current = (min(current[0], r[0]), min(current[1], r[1]),
                       max(current[2], r[2]), max(current[3], r[3]))
        else:
            merged.append(current)
            current = r
    merged.append(current)
    return merged

def extract_chat_foreground(img_path, mode='auto'):
    """
    分离微信聊天记录的前景（气泡+文字）与背景
    返回精细的二值掩膜，白色为前景，黑色为背景
    """
    img = cv2.imread(img_path)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # 转为RGB方便查看
    
    # 1. 自动判断深浅色模式（取图像四角的平均亮度）
    h, w = img.shape[:2]
    corners = img[0:10, 0:10].mean() + img[0:10, w-10:w].mean() + img[h-10:h, 0:10].mean() + img[h-10:h, w-10:w].mean()
    avg_bright = corners / 4
    
    # 2. 根据模式设定背景颜色的HSV范围（HSV对颜色差异更鲁棒）
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    if avg_bright > 127:  # 浅色模式
        # 背景为白色/浅灰色（低饱和度，高亮度）
        lower_bg = np.array([0, 0, 180])
        upper_bg = np.array([180, 30, 255])
    else:  # 深色模式
        # 背景为黑色/深灰色（低饱和度，低亮度）
        lower_bg = np.array([0, 0, 0])
        upper_bg = np.array([180, 255, 80])
    
    # 3. 提取背景区域掩膜
    mask_bg = cv2.inRange(hsv, lower_bg, upper_bg)
    
    # 4. 【关键】取反获得前景掩膜（气泡+文字+头像）
    mask_fg = cv2.bitwise_not(mask_bg)
    
    # 5. 精细形态学处理（解决圆角毛刺和文字空洞）
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    
    # 先闭运算：填充气泡内文字造成的黑色小洞（让气泡变得完整）
    mask_fg = cv2.morphologyEx(mask_fg, cv2.MORPH_CLOSE, kernel, iterations=1)
    # 再开运算：去除背景中零星的小噪点（保持边缘干净）
    mask_fg = cv2.morphologyEx(mask_fg, cv2.MORPH_OPEN, kernel, iterations=1)
    
    # 6. (可选) 边缘羽化或高斯模糊，让抠出的图更柔和
    # mask_fg = cv2.GaussianBlur(mask_fg, (3, 3), 0)
    
    # 7. 应用掩膜，把背景变透明或提取前景轮廓
    result = cv2.bitwise_and(img, img, mask=mask_fg)
    
    # 如果要画极其精细的轮廓（而不是方框），直接在掩膜上找轮廓
    contours, _ = cv2.findContours(mask_fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contour_img = img.copy()
    for cnt in contours:
        if cv2.contourArea(cnt) > 100:  # 过滤极小噪点
            # 这里画出的轮廓会完美贴合气泡的圆角，而不是矩形
            cv2.drawContours(contour_img, [cnt], -1, (0, 255, 0), 2)
    
    return mask_fg, result, contour_img

def get_left_panel_rect():
    """
    获取微信左侧边栏的矩形区域坐标 (x1, y1, x2, y2)
    """
    img = cv2.imread(img_path)
    if img is None:
        raise FileNotFoundError(f"图片未找到: {img_path}")
    h, w = img.shape[:2]
    # 1. 转为灰度图
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # 2. 二值化（阈值可调）
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    # 3. 形态学闭运算，连接竖直的边缘
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 15))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    # 4. 找轮廓
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # 5. 找到最左侧且面积较大的矩形
    left_rect = None
    max_area = 0
    for cnt in contours:
        x, y, w_box, h_box = cv2.boundingRect(cnt)
        area = w_box * h_box
        if area > max_area and x < w * 0.3:  # 限制在左侧30%区域
            max_area = area
            left_rect = (x, y, x + w_box, y + h_box)
    return left_rect

def main():
    result = capture_scroll_diff()
    if result is None:
        print("操作失败")
        return
    if result["has_diff"]:
        print(f"检测到差异，区域: {result['diff_rect']}")
    else:
        print("滚动前后无差异")
    print(f"截图1: {result['before_path']}")
    print(f"截图2: {result['after_path']}")

if __name__ == "__main__":
    # main()

    # 使用示例
    # mask, extracted, contours = extract_chat_foreground(r'E:\_proj\webot\output\wechat.png')
    # cv2.imshow('Foreground Mask', mask)      # 白色区域就是精细的前景
    # cv2.imshow('Extracted', extracted)       # 背景被去掉，只留前景
    # cv2.imshow('Fine Contours', contours)    # 圆角轮廓完美呈现
    # cv2.waitKey(0)

    # 调用函数
    # result_img, mask, boxes = segment_and_box_chat(r'E:\_proj\webot\output\wechat.png', min_area=300)

    # result_img, mask, boxes = segment_chat_robust(r'E:\_proj\webot\output\wechat.png', min_area=300)

    # cv2.imshow('Boxed Result', result_img)
    # cv2.imshow('Foreground Mask', mask)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()
    # # 打印矩形坐标
    # for i, (x1, y1, x2, y2) in enumerate(boxes):
    #     print(f"Box {i+1}: ({x1}, {y1}) -> ({x2}, {y2}), 宽度={x2-x1}, 高度={y2-y1}")
    
    # 1. 截取整个屏幕
    screenshot = pyautogui.screenshot()
    # 2. 在截图上绘制矩形（例如在坐标(100,100)到(300,200)之间）
    draw = ImageDraw.Draw(screenshot)

    xx, yy, ww, hh = get_title_bar_rect()
    draw.rectangle([(xx, yy), (xx + ww, yy + hh)], outline="blue", width=5)
    xx, yy, ww, hh = get_left_toolbar_rect()
    draw.rectangle([(xx, yy), (xx + ww, yy + hh)], outline="blue", width=5)
    xx, yy, ww, hh = get_search_bar_rect()
    draw.rectangle([(xx, yy), (xx + ww, yy + hh)], outline="blue", width=5)
    xx, yy, ww, hh = get_contact_list_rect()
    draw.rectangle([(xx, yy), (xx + ww, yy + hh)], outline="blue", width=5)
    xx, yy, ww, hh = get_chat_history_rect()
    draw.rectangle([(xx, yy), (xx + ww, yy + hh)], outline="blue", width=5)
    xx, yy, ww, hh = get_message_input_rect()
    draw.rectangle([(xx, yy), (xx + ww, yy + hh)], outline="blue", width=5)
    # 3. 显示或保存
    screenshot.show()
    # screenshot.save("screenshot_with_rect.png")
    pass