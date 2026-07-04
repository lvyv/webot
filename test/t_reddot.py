import cv2
from cv2.gapi import mask
import numpy as np

# agent / reddot_skill
AGENT_POLL_INTERVAL = 5.0
CHAT_LIST_WIDTH_RATIO = 0.30
CHAT_ITEM_HEIGHT = 68
CHAT_LIST_TOP_OFFSET = 80
CHAT_LIST_TAB_WIDTH = 0  # 聊天列表左侧的标签页宽度
RED_DOT_SAT_MIN = 80
RED_DOT_VAL_MIN = 80
RED_DOT_AREA_MIN = 35
RED_DOT_AREA_MAX = 45
RED_DOT_AREA_MIN2 = 150
RED_DOT_AREA_MAX2 = 160
RED_DOT_HUE_LOW1 = 0
RED_DOT_HUE_HIGH1 = 5
RED_DOT_HUE_LOW2 = 175
RED_DOT_HUE_HIGH2 = 180

def detect_red_dots(bgr_img, draw_result=True):
    hsv = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, np.array([RED_DOT_HUE_LOW1, RED_DOT_SAT_MIN, RED_DOT_VAL_MIN]),
                        np.array([RED_DOT_HUE_HIGH1, 255, 255]))
    mask2 = cv2.inRange(hsv, np.array([RED_DOT_HUE_LOW2, RED_DOT_SAT_MIN, RED_DOT_VAL_MIN]),
                        np.array([RED_DOT_HUE_HIGH2, 255, 255]))
    mask = cv2.bitwise_or(mask1, mask2)
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    # 显示处理后的mask（可选）
    # cv2.imshow('Red Dot Mask', mask)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    dots = []
    for c in contours:
        area = cv2.contourArea(c)
        if RED_DOT_AREA_MIN <= area <= RED_DOT_AREA_MAX or RED_DOT_AREA_MIN2 <= area <= RED_DOT_AREA_MAX2:
            M = cv2.moments(c)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                dots.append((cx, cy, area))
    
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

if __name__ == "__main__":
    # 测试 detect_red_dots 函数
    test_image_path = r"e:\abcd.png"  # 替换为你的测试图片路径
    bgr_img = cv2.imread(test_image_path)
    if bgr_img is None:
        print(f"无法读取图片: {test_image_path}")
    else:
        dots = detect_red_dots(bgr_img, draw_result=True)
        print(f"检测到的红点数量: {len(dots)}")
        for i, (cx, cy, area) in enumerate(dots):
            print(f"红点 {i + 1}: 中心=({cx}, {cy}), 面积={area}")