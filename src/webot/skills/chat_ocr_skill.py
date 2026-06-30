# -*- coding: utf-8 -*-
# skills/chat_ocr_skill.py

import cv2
import numpy as np
import glob
import os
from ..utils import CHAT_REGION_THRESHOLD, CHAT_MIN_CONTOUR_AREA, CHAT_BLEND_WIDTH, OCR_CONFIDENCE_THRESHOLD
from ..utils import get_logger
from .base import Skill

logger = get_logger(__name__)


def detect_chat_region(img_path1, img_path2, threshold=CHAT_REGION_THRESHOLD, min_area=CHAT_MIN_CONTOUR_AREA):
    img1 = cv2.imread(img_path1)
    img2 = cv2.imread(img_path2)
    if img1 is None or img2 is None:
        logger.error(f"无法读取参考图: {img_path1} 或 {img_path2}")
        return None

    if img1.shape != img2.shape:
        h, w = img1.shape[:2]
        img2 = cv2.resize(img2, (w, h))

    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    diff = cv2.absdiff(gray1, gray2)
    _, thresh = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)

    kernel = np.ones((5, 5), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    x_min, y_min = float('inf'), float('inf')
    x_max, y_max = float('-inf'), float('-inf')

    for contour in contours:
        if cv2.contourArea(contour) < min_area:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        x_min = min(x_min, x)
        y_min = min(y_min, y)
        x_max = max(x_max, x + w)
        y_max = max(y_max, y + h)

    if x_min == float('inf'):
        logger.warning("未检测到差异区域")
        return None

    logger.info(f"检测到聊天区域: ({x_min}, {y_min}) - ({x_max}, {y_max})")
    return (x_min, y_min, x_max, y_max)


def crop_images(image_paths, rect, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    x_start, y_start, x_end, y_end = rect
    cropped_paths = []

    for fp in image_paths:
        image = cv2.imread(fp)
        if image is None:
            logger.warning(f"跳过无法读取: {fp}")
            continue
        h, w = image.shape[:2]
        x_s = max(0, x_start)
        y_s = max(0, y_start)
        x_e = min(w, x_end)
        y_e = min(h, y_end)
        cropped = image[y_s:y_e, x_s:x_e]

        stem = os.path.splitext(os.path.basename(fp))[0]
        out_path = os.path.join(output_dir, f"{stem}.crop.png")
        cv2.imwrite(out_path, cropped)
        cropped_paths.append(out_path)

    logger.info(f"裁剪完成: {len(cropped_paths)} 张 -> {output_dir}")
    return cropped_paths


def _find_overlap_ncc(upper_img, lower_img, search_range=None):
    """
    比较 upper_img 底部 与 lower_img 顶部的 NCC 相似度，
    返回值表示两张图在垂直方向上的重叠行数。
    """
    h_u, w_u = upper_img.shape[:2]
    h_l, w_l = lower_img.shape[:2]

    if w_u != w_l:
        new_w = min(w_u, w_l)
        if w_u != new_w:
            upper_img = cv2.resize(upper_img, (new_w, int(h_u * new_w / w_u)))
        if w_l != new_w:
            lower_img = cv2.resize(lower_img, (new_w, int(h_l * new_w / w_l)))

    h_u, w_u = upper_img.shape[:2]
    h_l, _ = lower_img.shape[:2]

    if search_range is None:
        search_range = min(h_u, h_l) // 2
    max_overlap = min(h_u, h_l, search_range)
    if max_overlap < 1:
        return 0

    gray_u = cv2.cvtColor(upper_img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    gray_l = cv2.cvtColor(lower_img, cv2.COLOR_BGR2GRAY).astype(np.float32)

    best_overlap = 0
    best_ncc = -1.0

    for overlap in range(1, max_overlap + 1):
        bottom_of_upper = gray_u[h_u - overlap:h_u, :]
        top_of_lower = gray_l[:overlap, :]
        upper_norm = bottom_of_upper - np.mean(bottom_of_upper)
        lower_norm = top_of_lower - np.mean(top_of_lower)
        numerator = np.sum(upper_norm * lower_norm)
        denominator = np.sqrt(np.sum(upper_norm ** 2) * np.sum(lower_norm ** 2))
        ncc = numerator / (denominator + 1e-8)
        if ncc > best_ncc:
            best_ncc = ncc
            best_overlap = overlap

    return best_overlap


def _find_best_seam(overlapA, overlapB):
    h, w = overlapA.shape[:2]
    diff = np.sum((overlapA.astype(np.float32) - overlapB.astype(np.float32)) ** 2, axis=2)
    dp = diff.copy()
    path = np.zeros_like(dp, dtype=np.int32)

    for i in range(1, h):
        for j in range(w):
            prev = dp[i - 1, j]
            idx = j
            if j > 0 and dp[i - 1, j - 1] < prev:
                prev = dp[i - 1, j - 1]
                idx = j - 1
            if j < w - 1 and dp[i - 1, j + 1] < prev:
                prev = dp[i - 1, j + 1]
                idx = j + 1
            dp[i, j] += prev
            path[i, j] = idx

    seam = np.zeros(h, dtype=np.int32)
    seam[-1] = int(np.argmin(dp[-1]))
    for i in range(h - 2, -1, -1):
        seam[i] = int(path[i + 1, seam[i + 1]])

    return seam


def _blend_with_seam(top_img, bottom_img, overlap):
    hA, w = top_img.shape[:2]
    overlapA = top_img[hA - overlap:hA]
    overlapB = bottom_img[:overlap]
    seam = _find_best_seam(overlapA, overlapB)
    blended = np.zeros_like(overlapA)
    for i in range(overlap):
        s = seam[i]
        blended[i, :s] = overlapA[i, :s]
        blended[i, s:] = overlapB[i, s:]
    return blended


def _stitch_two(top_img, bottom_img, blend_width=25):
    overlap = _find_overlap_ncc(top_img, bottom_img)
    hA, w = top_img.shape[:2]
    hB, _ = bottom_img.shape[:2]

    if overlap <= 0 or overlap > min(hA, hB):
        logger.debug(f"未检测到重叠 (overlap={overlap})，直接拼接")
        return np.vstack((top_img, bottom_img))

    logger.debug(f"重叠行数: {overlap}")
    blended = _blend_with_seam(top_img, bottom_img, overlap)

    result = np.zeros((hA + hB - overlap, w, 3), dtype=np.uint8)
    result[:hA - overlap] = top_img[:hA - overlap]
    result[hA - overlap:hA] = blended
    result[hA:] = bottom_img[overlap:]

    return result


def stitch_images(cropped_paths, output_path, blend_width=CHAT_BLEND_WIDTH):
    if len(cropped_paths) < 2:
        logger.error("至少需要2张裁剪图才能拼接")
        return None

    imgs = []
    for fp in cropped_paths:
        img = cv2.imread(fp)
        if img is None:
            logger.error(f"无法读取: {fp}")
            return None
        imgs.append(img)

    result = imgs[-1]
    for i in range(len(imgs) - 2, -1, -1):
        logger.info(f"拼接第 {len(imgs)-i}/{len(imgs)} 张: {os.path.basename(cropped_paths[i])}")
        if imgs[i].shape[1] != result.shape[1]:
            new_w = min(result.shape[1], imgs[i].shape[1])
            result = cv2.resize(result, (new_w, int(result.shape[0] * new_w / result.shape[1])))
            imgs[i] = cv2.resize(imgs[i], (new_w, int(imgs[i].shape[0] * new_w / imgs[i].shape[1])))
        result = _stitch_two(result, imgs[i], blend_width)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    cv2.imwrite(output_path, result)
    logger.info(f"拼接完成: {output_path} ({result.shape[1]}x{result.shape[0]})")
    return output_path


def ocr_image(image_path, output_dir, conf_threshold=OCR_CONFIDENCE_THRESHOLD):
    from paddleocr import PaddleOCR
    import json

    ocr = PaddleOCR(use_doc_unwarping=False)
    result = ocr.predict(input=image_path)

    os.makedirs(output_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(image_path))[0]
    json_path = os.path.join(output_dir, f"{stem}_res.json")
    img_path_output = os.path.join(output_dir, f"{stem}_ocr_res_img.png")

    for res in result:
        res.save_to_img(output_dir)
        res.save_to_json(output_dir)

    texts = []
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        rec_texts = data.get("rec_texts", [])
        rec_scores = data.get("rec_scores", [])
        for txt, score in zip(rec_texts, rec_scores):
            if score >= conf_threshold:
                texts.append(txt)

    logger.info(f"OCR 完成: {len(texts)} 行文本 (置信度阈值={conf_threshold})")
    return {
        "json_path": json_path,
        "visual_path": img_path_output,
        "texts": texts,
    }


def read_chat_history(image_dir, output_dir=None, ref_images=None, threshold=CHAT_REGION_THRESHOLD, min_area=CHAT_MIN_CONTOUR_AREA, blend_width=CHAT_BLEND_WIDTH, conf_threshold=OCR_CONFIDENCE_THRESHOLD):
    image_files = sorted(glob.glob(os.path.join(image_dir, "*.png")))
    if len(image_files) < 2:
        logger.error(f"图片不足，{image_dir} 下至少需要2张PNG截图")
        return None

    if output_dir is None:
        output_dir = os.path.join(image_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    if ref_images is None:
        ref_images = image_files[:2]
    else:
        ref_images = [os.path.join(image_dir, r) if not os.path.isabs(r) else r for r in ref_images]

    rect = detect_chat_region(ref_images[0], ref_images[1], threshold, min_area)
    if rect is None:
        logger.error("聊天区域检测失败")
        return None

    cropped_paths = crop_images(image_files, rect, output_dir)

    stitched_path = os.path.join(output_dir, "stitched_result.png")
    result_path = stitch_images(cropped_paths, stitched_path, blend_width)
    if result_path is None:
        logger.error("拼接失败")
        return None

    ocr_result = ocr_image(result_path, output_dir, conf_threshold)

    return {
        "chat_region": rect,
        "cropped_count": len(cropped_paths),
        "stitched_path": result_path,
        "ocr_result": ocr_result,
    }


class ReadChatHistorySkill(Skill):
    name = "read_chat_history"
    description = "读取微信聊天记录（需先截图到目录）"
    parameters = {
        "image_dir": {"type": "string", "description": "截图目录路径"},
    }

    def execute(self, image_dir):
        result = read_chat_history(image_dir)
        if result is None:
            return "读取聊天记录失败"
        texts = result.get("ocr_result", {}).get("texts", [])
        return "\n".join(texts) if texts else "未读取到文本"
