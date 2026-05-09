import cv2
import numpy as np

# 读取图像（灰度或彩色均可）
img = cv2.imread('diff.png')
temp = cv2.add(img, 100)        # 所有像素加 50，自动饱和
result = np.where(img == 0, img, temp)  # 零值像素保持为 0
# 反转图像
inverted_img = cv2.bitwise_not(result)

# 保存或显示
cv2.imwrite('inverted.png', inverted_img)