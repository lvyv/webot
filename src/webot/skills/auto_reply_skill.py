import json
import os
import time
from datetime import datetime

import cv2
import numpy as np
import pyautogui

from .window_skill import activate_window
from .reddot_skill import get_wechat_rect, get_ocr_engine, get_unread_chats
from ..utils import (
    WECHAT_WINDOW_TITLE,
    WECHAT_WINDOW_CLSNAME,
    CHAT_LIST_WIDTH_RATIO,
    CHAT_ITEM_HEIGHT,
    CHAT_LIST_TOP_OFFSET,
    CHAT_LIST_TAB_WIDTH,
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
    cy = region_y + position["y"]

    pyautogui.click(cx, cy)
    logger.info(f"点击聊天项 (屏幕坐标: {cx}, {cy})")
    time.sleep(1.0)
    return True


def find_file_helper_y():
    """在聊天列表中寻找"文件传输助手"的 y 坐标（截图相对）。"""
    from .reddot_skill import capture_chat_list_region, ocr_chat_list, group_items_by_chat
    img = capture_chat_list_region()
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


def read_chat_area():
    rect = get_wechat_rect()
    if rect is None:
        return ""

    left, top, right, bottom = rect

    list_w = int((right - left) * CHAT_LIST_WIDTH_RATIO)
    msg_left = left + list_w
    msg_top = top + 120
    msg_right = right - 10
    msg_bottom = bottom - 150

    if msg_right <= msg_left or msg_bottom <= msg_top:
        logger.warning("聊天区域尺寸无效")
        return ""

    region = (msg_left, msg_top, msg_right - msg_left, msg_bottom - msg_top)

    try:
        pil_img = pyautogui.screenshot(region=region)
    except OSError:
        logger.error("截取聊天区域失败")
        return ""

    bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    tmp = os.path.join(os.environ.get("TEMP", "."), "webot_chat_area.png")
    cv2.imwrite(tmp, bgr)

    ocr = get_ocr_engine()
    result = ocr.predict(input=tmp)

    if not result:
        return ""

    page = result[0]
    texts = page.get("rec_texts", [])
    scores = page.get("rec_scores", [])
    lines = [t for t, s in zip(texts, scores) if s >= 0.5]

    return "\n".join(lines)


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
