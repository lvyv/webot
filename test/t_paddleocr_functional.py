#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 楚雄师范学院《自然语言处理》
# Python实用工具：提取nano banana2生成图片中的文本信息，并重新书写
#
# Awen. 2026.6
#
# 致谢
#
# Copyright (C) 2026 Awen <lvyu@cxtc.edu.cn>
# Licensed under the GNU LGPL v2.1 - https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html

"""
Run with::

    python ./t_paddleocr_functional.py
"""
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from paddleocr import PaddleOCR

IMAGE_PATH = r'E:\_proj\webot\test\images\framework.png'
CONF_THRESHOLD = 0.5
OUTPUT_DIR = r'E:\_proj\webot\test\images'


def erase_text_boxes(img, rec_boxes):
    """将检测到的文字框内像素替换为框外右侧第一个像素的颜色（逐行填充）"""
    h, w = img.shape[:2]
    result = img.copy()
    for box in rec_boxes:
        x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)
        if x1 >= x2 or y1 >= y2:
            continue
        sample_x = min(x1, w - 1)
        for y in range(y1, y2):
            color = result[y, sample_x].tolist()
            result[y, x1:x2] = color
    return result


def _try_find_font():
    import os
    candidates = [
        r'C:\Windows\Fonts\simhei.ttf',
        r'C:\Windows\Fonts\msyh.ttc',
        r'C:\Windows\Fonts\simsun.ttc',
        r'C:\Windows\Fonts\simfang.ttf',
        r'C:\Windows\Fonts\msyhbd.ttc',
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    for p in os.listdir(r'C:\Windows\Fonts'):
        full = os.path.join(r'C:\Windows\Fonts', p)
        if p.lower().endswith(('.ttf', '.ttc')) and os.path.isfile(full):
            return full
    return None


def _pick_font(font_path, size):
    try:
        return ImageFont.truetype(font_path, size)
    except Exception:
        return ImageFont.load_default()


def draw_high_conf_texts(img, rec_polys, rec_texts, rec_scores, conf_threshold=CONF_THRESHOLD):
    """将置信度 >= conf_threshold 的识别文字重新绘制到原始矩形区域内"""
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb)
    draw = ImageDraw.Draw(pil_img)

    font_path = _try_find_font()

    for poly, text, score in zip(rec_polys, rec_texts, rec_scores):
        if score < conf_threshold or not text:
            continue
        x1 = int(np.min(poly[:, 0]))
        y1 = int(np.min(poly[:, 1]))
        x2 = int(np.max(poly[:, 0]))
        y2 = int(np.max(poly[:, 1]))
        box_w = x2 - x1
        box_h = y2 - y1
        if box_w < 4 or box_h < 4:
            continue

        font_size = max(8, int(box_h * 0.7))
        font = _pick_font(font_path, font_size)

        while font_size > 6:
            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            if tw <= box_w:
                break
            font_size -= 1
            font = _pick_font(font_path, font_size)

        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        cx = x1 + (box_w - tw) // 2
        cy = y1 + (box_h - th) // 2

        draw.text((cx, cy), text, font=font, fill=(200, 200, 200))

    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def main():
    ocr = PaddleOCR(use_doc_unwarping=False)
    result = ocr.predict(input=IMAGE_PATH)
    page = result[0]

    rec_polys = page['rec_polys']
    rec_boxes = page['rec_boxes']
    rec_texts = page['rec_texts']
    rec_scores = page['rec_scores']

    img = cv2.imread(IMAGE_PATH)
    if img is None:
        raise FileNotFoundError(f"无法读取图片: {IMAGE_PATH}")

    import os
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    erased = erase_text_boxes(img, rec_boxes)
    erased_path = os.path.join(OUTPUT_DIR, 'erased.png')
    cv2.imwrite(erased_path, erased)
    print(f"[擦除完成] 已保存 {erased_path} （共擦除 {len(rec_boxes)} 个文字区域）")

    user_input = input("是否重新读取该文件（例如您手动修改过）并用于后续绘制？(y/n，默认 n): ").strip().lower()
    if user_input == 'y' or user_input == 'yes':
        # 重新读入 erased_path 中的图片，更新 erased 变量
        erased_reload = cv2.imread(erased_path)
        if erased_reload is not None:
            erased = erased_reload
            print("已重新读取文件内容，更新内存中的图片。")
        else:
            print("警告：重新读取失败，将使用内存中的擦除结果。")
    else:
        print("使用内存中的擦除结果。")

    drawn = draw_high_conf_texts(erased, rec_polys, rec_texts, rec_scores)
    drawn_path = os.path.join(OUTPUT_DIR, 'result.png')
    cv2.imwrite(drawn_path, drawn)
    high_conf = sum(1 for s in rec_scores if s >= CONF_THRESHOLD)
    print(f"[绘制完成] 已保存 {drawn_path} （置信度>={CONF_THRESHOLD} 的文字: {high_conf}/{len(rec_scores)})")


if __name__ == "__main__":
    main()
