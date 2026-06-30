import pyautogui
from ..utils import CONFIDENCE_LEVEL, RETRY_TIMES, RETRY_DELAY
from ..utils import get_logger, get_image_path
from .base import Skill

logger = get_logger(__name__)

def calculate_cursor_position(image_path, confidence=CONFIDENCE_LEVEL,
                              retry=RETRY_TIMES, delay=RETRY_DELAY, region=None):
    for attempt in range(1, retry + 1):
        try:
            location = pyautogui.locateCenterOnScreen(
                image=get_image_path(image_path),
                confidence=confidence,
                region=region,
            )
            if location:
                logger.info(f"定位成功: {image_path} -> ({location.x}, {location.y})")
                return {"x": location.x, "y": location.y, "found": True}
            else:
                logger.warning(f"尝试 {attempt}/{retry} 未找到: {image_path}")
        except Exception as e:
            logger.error(f"定位出错: {e}")
        if attempt < retry:
            import time
            time.sleep(delay)
    logger.error(f"最终失败，无法定位: {image_path}")
    return {"x": 0, "y": 0, "found": False}


class CalculateCursorPositionSkill(Skill):
    name = "calculate_cursor_position"
    description = "识别屏幕上的图形界面特征，计算其中心坐标"
    parameters = {
        "image_path": {"type": "string", "description": "图标文件名，如 contacts.png"},
        "confidence": {"type": "number", "description": "匹配精度(0-1)"},
        "region": {
            "type": "array",
            "description": "搜索区域 [left, top, width, height]，可选",
            "items": {"type": "integer"},
        },
    }

    def execute(self, image_path, confidence=CONFIDENCE_LEVEL, region=None):
        region = tuple(region) if region else None
        result = calculate_cursor_position(
            image_path, confidence=float(confidence), region=region,
        )
        if result["found"]:
            return f"已定位 {image_path} -> ({result['x']}, {result['y']})"
        return f"定位 {image_path} 失败"
