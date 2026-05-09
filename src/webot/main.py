#!/usr/bin/env python
# -*- coding: utf-8 -*-
# main.py
import os
import tempfile
from importlib.resources import files, as_file
from webot import config
from webot.skills import (
    resize_window, center_window, activate_window, maximize_window,
    click_ui_element, clear_text_field, find_and_input_text,
    scroll_repeatedly, wait_for_user_focus, read_chat_history,
)
from webot.utils import get_logger

logger = get_logger(__name__)


def get_image_path(filename):
    resource = files('webot.images') / filename
    with as_file(resource) as path:
        return str(path)


def get_screenshot_dir():
    path = os.path.join(os.getcwd(), "screenshots")
    os.makedirs(path, exist_ok=True)
    return path


def main():
    logger.info("启动 Webot 微信机器人")

    resize_window(config.WECHAT_WINDOW_TITLE,
                  config.DEFAULT_WINDOW_WIDTH,
                  config.DEFAULT_WINDOW_HEIGHT)
    center_window(config.WECHAT_WINDOW_TITLE)
    activate_window(config.WECHAT_WINDOW_TITLE)

    contacts_path = get_image_path(config.BTN_CONTACTS_IMAGE)
    click_ui_element(contacts_path)

    wait_for_user_focus(seconds=1, message="请确保微信聊天窗口已打开且可见")

    input_box_path = get_image_path(config.INPUT_SEARCH_CONTACT)
    success = find_and_input_text(
        image_path=input_box_path,
        text="口口",
        send_enter=True,
        confidence=config.CONFIDENCE_LEVEL
    )

    if not success:
        logger.error("搜索联系人失败，终止后续操作")
        return

    import pyautogui

    maximize_window("微信")
    wait_for_user_focus(seconds=1, message="请确保微信聊天窗口最大化")

    input_box_path = get_image_path(config.INPUT_MESSAGE_IN)
    clear_text_field(input_box_path)
    find_and_input_text(input_box_path, '浏览聊天历史记录...', send_enter=False)

    pyautogui.moveRel(0, -100, duration=0.5)

    shot_dir = get_screenshot_dir()
    num_shots = 5
    for idx in range(num_shots):
        scroll_repeatedly(times=10, direction="up")
        path = os.path.join(shot_dir, f"cap_{idx:03d}.png")
        pyautogui.screenshot(path)
        logger.info(f"截图已保存: {path}")

    result = read_chat_history(shot_dir)

    if result is None:
        logger.error("读取聊天记录失败")
        return

    rect = result["chat_region"]
    ocr = result["ocr_result"]
    texts = ocr["texts"]

    print("=" * 50)
    print(f"聊天区域: {rect}")
    print(f"裁剪图片: {result['cropped_count']} 张")
    print(f"拼接结果: {result['stitched_path']}")
    print(f"OCR 结果: {ocr['json_path']}")
    print("-" * 50)
    print("聊天记录:")
    for i, line in enumerate(texts, 1):
        print(f"  {i:>3}. {line}")
    print("=" * 50)

    logger.info(f"Webot 演示流程完成，共识别 {len(texts)} 条消息")

    resize_window(config.WECHAT_WINDOW_TITLE,
                  config.DEFAULT_WINDOW_WIDTH,
                  config.DEFAULT_WINDOW_HEIGHT)
    center_window(config.WECHAT_WINDOW_TITLE)
    activate_window(config.WECHAT_WINDOW_TITLE)
    logger.info("微信窗口已恢复原始尺寸，操作结束")

if __name__ == "__main__":
    main()