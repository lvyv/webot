import cv2
import numpy as np
import os
import glob


def compare_by_absdiff(img_path1, img_path2):
    # 1. 读取图像并转为灰度
    img1 = cv2.imread(img_path1)
    img2 = cv2.imread(img_path2)

    # 对齐大小（简单做法：强制统一为img1的尺寸，需确保两张图内容一致）
    if img1.shape != img2.shape:
        h, w = img1.shape[:2]
        img2 = cv2.resize(img2, (w, h))

    # 转为灰度图
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    # 2. (可选) 对灰度图进行高斯模糊，以减少高频噪声的影响
    gray1 = cv2.GaussianBlur(gray1, (21, 21), 0)
    gray2 = cv2.GaussianBlur(gray2, (21, 21), 0)

    # 3. 计算绝对差异图
    diff = cv2.absdiff(gray1, gray2)

    # 4. 对差异图进行阈值化，得到二值图像（只有黑和白）
    #    参数可调，这里是差异大于30的像素被设为255(白)
    _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
    # 5. (可选)形态学操作：闭运算，用于填充差异区域内部的小孔
    kernel = np.ones((5, 5), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    # 6. 查找重叠的差异区域轮廓
    #    cv2.RETR_EXTERNAL 只检索最外层的轮廓
    contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 7. 在原图上绘制矩形框
    img_result = img1.copy()  # 在img1上标注
    for contour in contours:
        # 忽略太小的区域（可能是噪点）
        if cv2.contourArea(contour) < 500:
            continue
        (x, y, w, h) = cv2.boundingRect(contour)
        cv2.rectangle(img_result, (x, y), (x + w, y + h), (0, 0, 255), 2)  # 红色框

    all_points = np.vstack(contours)

    # 2. 获得整体外接矩形
    # 2.1 垂直/水平矩形
    x, y, w, h = cv2.boundingRect(all_points)
    # 在图像上绘制这个矩形
    cv2.rectangle(img_result, (x, y), (x + w, y + h), (0, 255, 0), 2)

    return img_result, thresh, (x,y,x + w,y + h)


def crop_by_rect(img_path, rect):
    # 1. 读取图像
    image = cv2.imread(img_path)
    if image is None:
        print("错误：无法加载图像，请检查文件路径")
        exit()

    # 获取图像尺寸，用于边界检查
    height, width = image.shape[:2]

    # 2. 定义矩形框（需确保坐标在图像范围内）
    (x_start, y_start, x_end, y_end) = rect

    # 边界安全检查
    if x_end > width or y_end > height:
        print("错误：截取区域超出图像边界")
        exit()

    # 3. 切片截取
    cropped = image[y_start:y_end, x_start:x_end]

    # 4. 可选：显示截取效果
    cv2.imshow("Cropped Image", cropped)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # 5. 保存图像
    cv2.imwrite(f'{img_path}.crop.png', cropped)

if __name__ == '__main__':
    # 使用示例
    result_img, binary_img, rect = compare_by_absdiff('output/cap_002.png', 'output/cap_001.png')
    # 在 imshow 之前或之后, 移动名为 'Differences' 的窗口
    cv2.namedWindow('Differences')          # 显式创建窗口
    cv2.moveWindow('Differences', 0, 0)     # 将窗口移动到屏幕左上角
    # cv2.imshow('Differences', result_img)   # 显示图片
    # cv2.imshow('Differences', result_img)
    # cv2.imshow('Binary Diff', binary_img)

    image_files = glob.glob("output/cap_*.png")
    image_files.sort()  # 确保文件名顺序正确
    for fp in image_files:
        crop_by_rect(fp, rect)

    cv2.waitKey(0)
    cv2.destroyAllWindows()