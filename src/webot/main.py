#!/usr/bin/env python
# -*- coding: utf-8 -*-
# main.py

import sys
from importlib import resources

from webot import config
from webot.skills import (
    resize_window, center_window, activate_window,
    find_and_input_text, scroll_repeatedly, wait_for_user_focus
)
from webot.utils import get_logger

logger = get_logger(__name__)

def get_image_path(filename):
    """获取打包在 images 目录下的图片文件路径"""
    with resources.path("webot.images", filename) as path:
        return str(path)

def main():
    logger.info("启动 Webot 微信机器人")

    # 1. 准备微信窗口
    resize_window(config.WECHAT_WINDOW_TITLE,
                  config.DEFAULT_WINDOW_WIDTH,
                  config.DEFAULT_WINDOW_HEIGHT)
    center_window(config.WECHAT_WINDOW_TITLE)
    activate_window(config.WECHAT_WINDOW_TITLE)

    # 2. 等待用户确认
    wait_for_user_focus(seconds=2, message="请确保微信聊天窗口已打开且可见")

    # 3. 发送消息
    input_box_path = get_image_path(config.INPUT_BOX_IMAGE)
    success = find_and_input_text(
        image_path=input_box_path,
        text="口口",
        send_enter=True,
        confidence=config.CONFIDENCE_LEVEL
    )

    if not success:
        logger.error("消息发送失败，终止后续操作")
        return

    # 4. 后续操作示例
    import pyautogui
    import time
    time.sleep(1)
    pyautogui.moveRel(200, 50, duration=0.5)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(1)

    # 5. 滚动
    scroll_repeatedly(amount=10, times=10, direction="down")

    logger.info("Webot 流程执行完毕")

if __name__ == "__main__":
    main()