import cv2
import numpy as np

# 直接以灰度模式读取图像
# 第二个参数 0 是 cv2.IMREAD_GRAYSCALE 的简写
img0 = cv2.imread('output/cap_002.png')
img1 = cv2.imread('output/cap_003.png')

# 转为灰度图
gray_img0 = cv2.cvtColor(img0, cv2.COLOR_BGR2GRAY)
gray_img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)

# 显示灰度图
# cv2.imshow('Grayscale Image', gray_img0)
# cv2.imshow('Grayscale Image', gray_img1)

diff = cv2.absdiff(gray_img0, gray_img1)



_, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)


# 5. (可选)形态学操作：闭运算，用于填充差异区域内部的小孔
kernel = np.ones((5, 5), np.uint8)
thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

(contours, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

print(type(contours))

cv2.imshow('Grayscale Image', thresh)


# 等待按键，然后关闭窗口
cv2.waitKey(0)
cv2.destroyAllWindows()
