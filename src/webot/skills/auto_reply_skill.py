import json
import os
import tempfile
import time
from datetime import datetime

import cv2
import numpy as np
import pyautogui

from webot.utils import config

from .window_skill import hide_window, show_window
from .reddot_skill import get_wechat_rect, get_unread_chats
from .panel_rect_skill import get_chat_history_rect
from .scroll_skill import scroll_repeatedly
from .chat_ocr_skill import stitch_images
from ..utils.ocr import get_ocr_engine
from ..utils import (
    WECHAT_WINDOW_TITLE,
    WECHAT_WINDOW_CLSNAME,
    CHAT_LIST_WIDTH_RATIO,
    CHAT_ITEM_HEIGHT,
    CHAT_LIST_TOP_OFFSET,
    CHAT_LIST_TAB_WIDTH,
    OCR_CONFIDENCE_THRESHOLD,
)
from ..utils import get_logger
from .base import Skill

logger = get_logger(__name__)

RULES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "conf", "rules.json")


def load_rules(rules_path=None):
    path = rules_path or RULES_PATH
    if not os.path.exists(path):
        logger.warning(f"规则文件不存在: {path}，使用默认规则")
        return _default_rules()
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"读取规则文件失败: {e}")
        return _default_rules()


def _default_rules():
    return {
        "version": 1,
        "auto_reply_groups": [],
        "auto_reply_contacts": [],
        "reply_patterns": [
            {"name": "默认回复", "match_type": "always",
             "response": "您好，您的消息我已收到，会尽快回复。"}
        ],
        "reply_mode": "first_match",
    }


def save_default_rules(rules_path=None):
    path = rules_path or RULES_PATH
    rules = _default_rules()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)
    logger.info(f"已生成默认规则文件: {path}")


def should_auto_reply(chat_name, rules):
    if chat_name in rules.get("auto_reply_groups", []):
        return True
    if chat_name in rules.get("auto_reply_contacts", []):
        return True
    return False


def select_reply(rules):
    now = datetime.now()
    current_minutes = now.hour * 60 + now.minute

    for pattern in rules.get("reply_patterns", []):
        mt = pattern.get("match_type", "always")
        if mt == "always":
            return pattern["response"]
        elif mt == "time_range":
            t_start = pattern.get("time_start", "00:00")
            t_end = pattern.get("time_end", "23:59")
            sh, sm = (int(x) for x in t_start.split(":"))
            eh, em = (int(x) for x in t_end.split(":"))
            start_m = sh * 60 + sm
            end_m = eh * 60 + em
            if start_m <= end_m:
                if start_m <= current_minutes < end_m:
                    return pattern["response"]
            else:
                if current_minutes >= start_m or current_minutes < end_m:
                    return pattern["response"]

    return None


def click_chat_by_position(position):
    """基于红点 position（截图相对坐标）点击聊天项。"""
    cx = position['x']
    cy = position['y']
    pyautogui.click(cx, cy)
    logger.info(f"点击聊天项 (屏幕坐标: {cx}, {cy})")
    time.sleep(0.5)
    return True


def find_file_helper_y():
    """在聊天列表中寻找"文件传输助手"的 y 坐标（截图相对）。"""
    from .reddot_skill import capture_chat_list_region, ocr_chat_list, group_items_by_chat
    img, _, _ = capture_chat_list_region()
    if img is None:
        return None
    items = ocr_chat_list(img)
    for it in items:
        if "文件传输助手" in it["text"]:
            return int(it["cy"])
    return None


def send_confirm_request(helper_y, chat_name, reply_text):
    """点击文件传输助手，发送确认消息给主人。"""
    rect = get_wechat_rect()
    if rect is None:
        return False
    left, top, right, bottom = rect
    cw = right - left
    list_w = int(cw * CHAT_LIST_WIDTH_RATIO)
    region_x = left + CHAT_LIST_TAB_WIDTH
    region_y = top + CHAT_LIST_TOP_OFFSET
    region_w = list_w - CHAT_LIST_TAB_WIDTH

    cx = region_x + region_w // 2
    cy = region_y + helper_y
    pyautogui.click(cx, cy)
    time.sleep(0.5)

    confirm_msg = (
        f"【需确认回复】\n联系人：{chat_name}\n"
        f"建议回复：{reply_text}\n\n"
        f"请回复（任选其一）：\n@同意\n@拒绝\n@修改:新的回复内容"
    )
    return send_reply(confirm_msg)


def read_chat_area(scroll_times=0, scroll_amount=30):
    """读取当前选中的聊天区域内容。

    Args:
        scroll_times: 向上滚动次数（用于读取更多历史消息）
        scroll_amount: 每次滚动量

    Returns:
        拼接后的聊天文本
    """
    rect = get_chat_history_rect()
    if rect is None:
        logger.warning("无法获取聊天历史区域")
        return ""

    region = (rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1])
    if region[2] <= 0 or region[3] <= 0:
        logger.warning("聊天历史区域尺寸无效")
        return ""

    screenshots = []
    try:
        pil_img = pyautogui.screenshot(region=region)
        screenshots.append(cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR))
    except OSError:
        logger.error("截取聊天区域失败")
        return ""

    for _ in range(scroll_times):
        scroll_repeatedly(amount=scroll_amount, times=1, direction="up")
        time.sleep(0.3)
        try:
            pil_img = pyautogui.screenshot(region=region)
            screenshots.append(cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR))
        except OSError:
            break

    if len(screenshots) == 0:
        return ""

    if len(screenshots) > 1:
        tmp_dir = tempfile.mkdtemp(prefix="webot_chat_")
        paths = []
        for i, img in enumerate(screenshots):
            p = os.path.join(tmp_dir, f"frame_{i}.png")
            cv2.imwrite(p, img)
            paths.append(p)
        stitched_path = os.path.join(tmp_dir, "stitched.png")
        stitch_images(paths, stitched_path)
        final_img = cv2.imread(stitched_path)
        if final_img is None:
            final_img = screenshots[0]
    else:
        final_img = screenshots[0]

    tmp = os.path.join(tempfile.gettempdir(), "webot_chat_area_final.png")
    cv2.imwrite(tmp, final_img)

    ocr = get_ocr_engine()
    result = ocr.predict(input=tmp)

    if not result:
        return ""

    page = result[0]
    texts = page.get("rec_texts", [])
    scores = page.get("rec_scores", [])
    lines = [t for t, s in zip(texts, scores) if s >= OCR_CONFIDENCE_THRESHOLD]

    return "\n".join(lines)


def process_single_chat(m, scroll_times=0, scroll_amount=30):
    """封装点击联系人 + 读取聊天记录的操作。

    Args:
        m: 聊天联系人信息 dict，需包含 chat_name, position 等
        scroll_times: 读取时向上滚动截图次数
        scroll_amount: 每次滚动量

    Returns:
        聊天文本内容，失败返回空字符串
    """
    name = m.get("chat_name", "")
    position = m.get("position")
    if not position:
        logger.warning(f"[{name}] 缺少 position 信息，跳过")
        return ""

    if not click_chat_by_position(position):
        logger.warning(f"[{name}] 点击失败")
        return ""

    time.sleep(0.5)

    hide_window(config.APP_NAME)
    time.sleep(0.3)

    # messages = read_chat_area(scroll_times=scroll_times, scroll_amount=scroll_amount)
    messages = 'reading chat area...'
    show_window(config.APP_NAME)

    click_chat_by_position(position)

    if messages:
        logger.info(f"[{name}] 聊天内容:\n{messages[:200]}")
    else:
        logger.warning(f"[{name}] 未读取到聊天消息")

    return messages


def send_reply(reply_text):
    import pyperclip

    rect = get_wechat_rect()
    if rect is None:
        return False

    left, top, right, bottom = rect
    list_w = int((right - left) * CHAT_LIST_WIDTH_RATIO)
    input_x = left + list_w + ((right - left) - list_w) // 2
    input_y = bottom - 80

    pyautogui.click(input_x, input_y)
    time.sleep(0.3)
    pyperclip.copy(reply_text)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.3)
    pyautogui.press("enter")
    logger.info(f"已回复: {reply_text[:50]}...")
    return True


def process_chat(chat_name, item_index, rules):
    logger.info(f"处理聊天: [{chat_name}] (item #{item_index})")

    # if not activate_window(WECHAT_WINDOW_TITLE, WECHAT_WINDOW_CLSNAME):
    #     logger.error("无法激活微信窗口")
    #     return False

    # time.sleep(0.5)

    if not click_chat_by_position({"y": item_index * CHAT_ITEM_HEIGHT + CHAT_ITEM_HEIGHT // 2}):
        return False

    messages = read_chat_area()
    if messages:
        logger.info(f"[{chat_name}] 最新消息:\n{messages[:200]}")
    else:
        logger.warning("未读取到聊天消息")

    reply_text = select_reply(rules)
    if not reply_text:
        logger.info(f"[{chat_name}] 无匹配回复模式，跳过")
        return False

    return send_reply(reply_text)


def auto_reply_cycle(rules=None):
    return get_unread_chats()


class ProcessChatSkill(Skill):
    name = "process_chat"
    description = "处理指定聊天的未读消息（点击、读取、回复）"
    parameters = {
        "chat_name": {"type": "string", "description": "聊天名称"},
        "item_index": {"type": "integer", "description": "聊天项序号"},
    }

    def execute(self, chat_name, item_index):
        rules = load_rules()
        ok = process_chat(chat_name, int(item_index), rules)
        return f"已处理 {chat_name}" if ok else f"处理 {chat_name} 失败"


class SendReplySkill(Skill):
    name = "send_reply"
    description = "向当前打开的聊天发送回复文本"
    parameters = {
        "reply_text": {"type": "string", "description": "回复内容"},
    }

    def execute(self, reply_text):
        ok = send_reply(reply_text)
        return f"已回复: {reply_text[:50]}" if ok else "回复失败"


class ClickChatSkill(Skill):
    name = "click_chat"
    description = "按位置点击聊天列表中的项"
    parameters = {
        "position_y": {"type": "integer", "description": "聊天项在截图中的 y 坐标"},
    }

    def execute(self, position_y):
        ok = click_chat_by_position({"y": int(position_y)})
        return f"已点击聊天项 (y={position_y})" if ok else "点击失败"
