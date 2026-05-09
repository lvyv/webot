import cv2
import numpy as np

def brute_force_overlap(img0, img1, max_search=800):
    grayA = cv2.cvtColor(img0, cv2.COLOR_BGR2GRAY)
    grayB = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    hA = grayA.shape[0]
    best_score = float('inf')
    best_overlap = 0
    for overlap in range(50, max_search):
        partA = grayA[hA-overlap:hA]
        partB = grayB[:overlap]
        if partA.shape != partB.shape:
            continue
        diff = np.mean((partA - partB)**2)
        if diff < best_score:
            best_score = diff
            best_overlap = overlap
    print("best_overlap:", best_overlap, "score:", best_score)
    return best_overlap

def find_best_seam(overlapA, overlapB):
    """
    用动态规划找最小差异路径（垂直 seam）
    """
    h, w = overlapA.shape[:2]

    diff = np.sum((overlapA.astype(np.float32) - overlapB.astype(np.float32))**2, axis=2)

    dp = diff.copy()
    path = np.zeros_like(dp, dtype=np.int32)

    for i in range(1, h):
        for j in range(w):
            prev = dp[i-1, j]
            idx = j

            if j > 0 and dp[i-1, j-1] < prev:
                prev = dp[i-1, j-1]
                idx = j-1
            if j < w-1 and dp[i-1, j+1] < prev:
                prev = dp[i-1, j+1]
                idx = j+1

            dp[i, j] += prev
            path[i, j] = idx

    seam = np.zeros(h, dtype=np.int32)
    seam[-1] = np.argmin(dp[-1])

    for i in range(h-2, -1, -1):
        seam[i] = path[i+1, seam[i+1]]

    return seam

def blend_with_seam(img0, img1, overlap):
    hA, w = img0.shape[:2]
    overlapA = img0[hA - overlap:hA]
    overlapB = img1[:overlap]
    seam = find_best_seam(overlapA, overlapB)
    blended = np.zeros_like(overlapA)
    for i in range(overlap):
        s = seam[i]
        blended[i, :s] = overlapA[i, :s]
        blended[i, s:] = overlapB[i, s:]
    return blended

def stitch(img0, img1):
    overlap = brute_force_overlap(img0, img1)
    hA, w = img0.shape[:2]
    hB, _ = img1.shape[:2]
    # 无重叠 fallback
    if overlap <= 0 or overlap > min(hA, hB):
        print("⚠️ overlap异常，直接拼接")
        result = np.vstack((img0, img1))
        return result
    # seam融合
    blended = blend_with_seam(img0, img1, overlap)
    # 拼接
    result = np.zeros((hA + hB - overlap, w, 3), dtype=np.uint8)
    result[:hA-overlap] = img0[:hA - overlap]
    result[hA-overlap:hA] = blended
    result[hA:] = img1[overlap:]
    cv2.imwrite("blended.png", blended)
    cv2.imwrite("debug_A_bottom.png", img0[hA - overlap:hA])
    cv2.imwrite("debug_B_top.png", img1[:overlap])
    return result

if __name__ == '__main__':
    # ========= 使用 =========
    # 读取图片
    imgA = cv2.imread('output/cap_004.png.crop.png')
    imgB = cv2.imread('output/after_result.png')
    res = stitch(imgA, imgB)
    cv2.imwrite("output/after_result.png", res)