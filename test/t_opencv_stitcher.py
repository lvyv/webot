import cv2
import numpy as np


def find_overlap_by_features(bottom_img, top_img, min_matches=10):
    """
    使用特征匹配查找两幅图片的重叠区域
    :param bottom_img: 下方图片
    :param top_img:    上方图片
    :param min_matches: 最小匹配数量
    :return: (overlap_rows, offset_x), overlap_rows为检测到的重叠行数，offset_x为水平偏移
    """
    h_b, w_b = bottom_img.shape[:2]
    h_t, w_t = top_img.shape[:2]

    if w_b != w_t:
        return 0, 0

    gray_b = cv2.cvtColor(bottom_img, cv2.COLOR_BGR2GRAY)
    gray_t = cv2.cvtColor(top_img, cv2.COLOR_BGR2GRAY)

    orb = cv2.ORB_create(nfeatures=2000)
    kp_b, des_b = orb.detectAndCompute(gray_b, None)
    kp_t, des_t = orb.detectAndCompute(gray_t, None)

    if des_b is None or des_t is None or len(kp_b) < min_matches or len(kp_t) < min_matches:
        return 0, 0

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = matcher.knnMatch(des_b, des_t, k=2)

    good_matches = []
    for m_n in matches:
        if len(m_n) == 2:
            if m_n[0].distance < 0.75 * m_n[1].distance:
                good_matches.append(m_n[0])

    if len(good_matches) < min_matches:
        return 0, 0

    src_pts = np.float32([kp_b[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp_t[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

    M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    if M is None:
        return 0, 0

    inliers = mask.ravel() == 1
    inlier_count = np.sum(inliers)
    if inlier_count < min_matches:
        return 0, 0

    translation_y = M[1, 2]

    inlier_src = src_pts[inliers]
    inlier_dst = dst_pts[inliers]

    median_y_src = np.median(inlier_src[:, 0, 1])
    median_y_dst = np.median(inlier_dst[:, 0, 1])

    overlap_rows = int(round(abs(median_y_dst - median_y_src)))
    overlap_rows = max(0, min(overlap_rows, min(h_b, h_t) - 1))

    return overlap_rows, 0


def find_overlap_by_template(bottom_img, top_img, search_height_ratio=0.5):
    """
    使用模板匹配查找垂直重叠区域
    :param bottom_img: 下方图片
    :param top_img:   上方图片  
    :param search_height_ratio: 搜索高度占图片比例
    :return: overlap_rows
    """
    h_b, w_b = bottom_img.shape[:2]
    h_t, w_t = top_img.shape[:2]
    
    if w_b != w_t:
        return 0
        
    gray_b = cv2.cvtColor(bottom_img, cv2.COLOR_BGR2GRAY)
    gray_t = cv2.cvtColor(top_img, cv2.COLOR_BGR2GRAY)
    
    search_h = int(min(h_b, h_t) * search_height_ratio)
    if search_h < 10:
        return 0
        
    template = gray_b[h_b - search_h:, :]
    
    result = cv2.matchTemplate(gray_t, template, cv2.TM_CCOEFF_NORMED)
    
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    
    if max_val < 0.3:
        return 0
    
    matched_row = max_loc[1]
    
    overlap = search_h - matched_row
    overlap = max(0, min(overlap, min(h_b, h_t)))
    
    return overlap


def find_overlap_by_sift(bottom_img, top_img, min_matches=10, ratio_threshold=0.75):
    """
    使用SIFT特征匹配查找重叠区域
    :param bottom_img: 下方图片
    :param top_img:   上方图片  
    :param min_matches: 最小匹配数
    :param ratio_threshold: Lowe比率阈值
    :return: (overlap_rows, offset_x)  
    """
    h_b, w_b = bottom_img.shape[:2]
    h_t, w_t = top_img.shape[:2]
    
    if w_b != w_t:
        return 0, 0
    
    gray_b = cv2.cvtColor(bottom_img, cv2.COLOR_BGR2GRAY)
    gray_t = cv2.cvtColor(top_img, cv2.COLOR_BGR2GRAY)
    
    try:
        sift = cv2.SIFT_create(nfeatures=2000)
    except AttributeError:
        return 0, 0
    
    kp_b, des_b = sift.detectAndCompute(gray_b, None)
    kp_t, des_t = sift.detectAndCompute(gray_t, None)
    
    if des_b is None or des_t is None or len(kp_b) < min_matches or len(kp_t) < min_matches:
        return 0, 0
    
    matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
    matches = matcher.knnMatch(des_b, des_t, k=2)
    
    good = []
    for m_n in matches:
        if len(m_n) == 2:
            if m_n[0].distance < ratio_threshold * m_n[1].distance:
                good.append(m_n[0])
    
    if len(good) < min_matches:
        return 0, 0
    
    src_pts = np.float32([kp_b[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp_t[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    
    M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    if M is None:
        return 0, 0
    
    inliers = mask.ravel() == 1
    if np.sum(inliers) < min_matches:
        return 0, 0
    
    y_translation = int(abs(M[1, 2]))
    overlap_rows = max(0, min(y_translation, min(h_b, h_t) - 1))
    
    return overlap_rows, 0


def find_vertical_overlap(bottom_img, top_img, search_range=None):
    """
    查找 bottom_img 底部与 top_img 顶部的重叠行数
    :param bottom_img: 下方图片 (H_b, W, C)
    :param top_img:    上方图片 (H_t, W, C)
    :param search_range: 搜索范围（最大可能重叠高度），默认 min(H_b, H_t)//2
    :return: overlap_rows: 重叠的行数
    """
    h_b, w_b = bottom_img.shape[:2]
    h_t, w_t = top_img.shape[:2]
    assert w_b == w_t, "图片宽度不一致，请先resize到相同宽度"

    if search_range is None:
        search_range = min(h_b, h_t) // 2

    # 只取有效搜索范围
    max_overlap = min(h_b, h_t, search_range)
    if max_overlap < 1:
        return 0

    best_overlap = 0
    best_ncc = -1.0

    # 将图片转为灰度用于计算相关性
    gray_b = cv2.cvtColor(bottom_img, cv2.COLOR_BGR2GRAY)
    gray_t = cv2.cvtColor(top_img, cv2.COLOR_BGR2GRAY)

    # 遍历候选重叠行数
    for overlap in range(1, max_overlap + 1):
        # 底部图片的最后 overlap 行
        bottom_roi = gray_b[h_b - overlap:h_b, :]
        # 顶部图片的前 overlap 行
        top_roi = gray_t[:overlap, :]

        # 计算归一化互相关（NCC）
        bottom_norm = bottom_roi - np.mean(bottom_roi)
        top_norm = top_roi - np.mean(top_roi)
        numerator = np.sum(bottom_norm * top_norm)
        denominator = np.sqrt(np.sum(bottom_norm**2) * np.sum(top_norm**2))
        ncc = numerator / (denominator + 1e-8)

        if ncc > best_ncc:
            best_ncc = ncc
            best_overlap = overlap

    return best_overlap


def blend_overlap_region(bottom_part, top_part, blend_width=None):
    """
    对重叠区域进行线性融合
    """
    overlap_h = bottom_part.shape[0]
    if blend_width is None or blend_width >= overlap_h:
        alpha = np.linspace(0, 1, overlap_h, dtype=np.float32).reshape(overlap_h, 1, 1)
    else:
        alpha = np.ones((overlap_h, 1, 1), dtype=np.float32)
        alpha[:blend_width] = np.linspace(0, 1, blend_width, dtype=np.float32).reshape(blend_width, 1, 1)
        alpha[-blend_width:] = np.linspace(1, 0, blend_width, dtype=np.float32).reshape(blend_width, 1, 1)
    blended = (1 - alpha) * bottom_part + alpha * top_part
    return blended.astype(np.uint8)


def merge_stitch(image_paths, output_path, method='template', blend_width=30):
    """
    多图垂直拼接
    :param image_paths: 图片路径列表，按从上到下顺序
    :param output_path: 输出路径
    :param method: 'template', 'features', 或 'ncc'
    :param blend_width: 融合宽度
    """
    if len(image_paths) < 2:
        raise ValueError("至少需要2张图片")
    
    imgs = [cv2.imread(p) for p in image_paths]
    for i, img in enumerate(imgs):
        if img is None:
            raise FileNotFoundError(f"无法读取: {image_paths[i]}")
    
    for i in range(1, len(imgs)):
        if imgs[0].shape[1] != imgs[i].shape[1]:
            new_w = min(imgs[0].shape[1], imgs[i].shape[1])
            scale = new_w / imgs[i].shape[1]
            imgs[i] = cv2.resize(imgs[i], (new_w, int(imgs[i].shape[0] * scale)))
            imgs[i] = cv2.resize(imgs[i], (imgs[0].shape[1], imgs[i].shape[0]))
    
    result = imgs[0]
    
    for i in range(1, len(imgs)):
        if method == 'template':
            overlap = find_overlap_by_template(result, imgs[i])
        elif method == 'features':
            overlap, _ = find_overlap_by_features(result, imgs[i])
        else:
            overlap = find_vertical_overlap(result, imgs[i])
        
        print(f"图{i}与图{i-1}重叠: {overlap}")
        
        if overlap <= 0:
            result = np.vstack([result, imgs[i]])
        else:
            top_overlap = imgs[i][imgs[i].shape[0] - overlap:, :, :]
            bottom_overlap = result[:overlap, :, :]
            blended = blend_overlap_region(bottom_overlap, top_overlap, blend_width)
            result = np.vstack([result[overlap:, :, :], blended, imgs[i][imgs[i].shape[0] - overlap:, :, :]])
    
    cv2.imwrite(output_path, result)
    print(f"保存至: {output_path}")


def merge_vertical_overlap(bottom_path, top_path, output_path, method='features', auto_detect=True, overlap_rows=None, blend_width=30):
    """
    垂直拼接两幅有重叠区域的图片，下方图片底部与上方图片顶部重合
    :param bottom_path: 下方图片路径 (001.png)
    :param top_path:    上方图片路径 (000.png)
    :param output_path: 输出路径
    :param method:      'features'使用特征匹配，'ncc'使用NCC相关
    :param auto_detect:  是否自动检测重叠行数；若为False，需手动指定overlap_rows
    :param overlap_rows:  手动指定的重叠行数（当auto_detect=False时使用）
    :param blend_width:   融合渐变宽度（像素）
    """
    # 读取图片
    bottom = cv2.imread(bottom_path)
    top = cv2.imread(top_path)
    if bottom is None or top is None:
        raise FileNotFoundError("无法读取图片，请检查路径")

    h_b, w_b = bottom.shape[:2]
    h_t, w_t = top.shape[:2]

    # 确保宽度一致（若不一致，将较宽的缩放至较窄的宽度）
    if w_b != w_t:
        print("警告：图片宽度不一致，将自动缩放至较小宽度")
        new_width = min(w_b, w_t)
        if w_b != new_width:
            bottom = cv2.resize(bottom, (new_width, int(h_b * new_width / w_b)))
            h_b, w_b = bottom.shape[:2]
        if w_t != new_width:
            top = cv2.resize(top, (new_width, int(h_t * new_width / w_t)))
            h_t, w_t = top.shape[:2]

    # 确定重叠行数
    if auto_detect:
        if method == 'features':
            overlap, _ = find_overlap_by_features(bottom, top)
            print(f"特征匹配检测重叠行数: {overlap}")
        else:
            overlap = find_vertical_overlap(bottom, top)
            print(f"NCC检测重叠行数: {overlap}")
    else:
        if overlap_rows is None:
            raise ValueError("当auto_detect=False时，必须指定overlap_rows")
        overlap = overlap_rows
        if overlap > min(h_b, h_t):
            raise ValueError("重叠行数超过最小图片高度")

    # 无重叠或重叠≤0，直接拼接
    if overlap <= 0:
        print("未检测到重叠区域，直接垂直拼接")
        result = np.vstack([top, bottom])
        cv2.imwrite(output_path, result)
        return

    # 分离非重叠与重叠区域
    top_non_overlap = top[:h_t - overlap, :, :]          # 上方图片的非重叠顶部
    bottom_non_overlap = bottom[overlap:, :, :]          # 下方图片的非重叠底部
    top_overlap = top[h_t - overlap:h_t, :, :]           # 上方图片的重叠区域（底部）
    bottom_overlap = bottom[:overlap, :, :]              # 下方图片的重叠区域（顶部）

    # 对重叠区域进行融合
    blended_overlap = blend_overlap_region(bottom_overlap, top_overlap, blend_width=blend_width)

    # 拼接最终图片
    result = np.vstack([top_non_overlap, blended_overlap, bottom_non_overlap])
    cv2.imwrite(output_path, result)
    print(f"拼接完成，保存至: {output_path}")


# 测试示例
if __name__ == "__main__":
    import sys
    
    cv2.namedWindow("Test", cv2.WINDOW_NORMAL)
    cv2.moveWindow("Test", 0, 0)
    
    bottom = cv2.imread("test/images/cap_000.png")
    top = cv2.imread("test/images/cap_001.png")
    
    if bottom is None or top is None:
        print("error: can't read images")
        sys.exit(1)
    
    print(f"bottom: {bottom.shape}, top: {top.shape}")
    
    # 测试各方法
    print("\n=== template ===")
    ov1 = find_overlap_by_template(bottom, top)
    print(f"overlap: {ov1}")
    
    print("\n=== features (ORB) ===")
    ov2, _ = find_overlap_by_features(bottom, top)
    print(f"overlap: {ov2}")
    
    print("\n=== SIFT ===")
    ov3, _ = find_overlap_by_sift(bottom, top)
    print(f"overlap: {ov3}")
    
    print("\n=== NCC ===")
    ov4 = find_vertical_overlap(bottom, top)
    print(f"overlap: {ov4}")
    
    # 使用template方法拼接
    merge_stitch(
        ["test/output/cap_001.png.crop.png", "test/output/cap_000.png.crop.png"],
        "test/output/merged.png",
        method='template',
        blend_width=25
    )