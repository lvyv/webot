#!/usr/bin/env python
# -*- coding: utf-8 -*-
# main.py
from importlib.resources import files, as_file
from webot import config
from webot.skills import (
    resize_window, center_window, activate_window, maximize_window,
    click_ui_element, clear_text_field, find_and_input_text, scroll_repeatedly, wait_for_user_focus
)
from webot.utils import get_logger

logger = get_logger(__name__)

# def get_image_path(filename):
#     """获取打包在 images 目录下的图片文件路径"""
#     with resources.path("webot.images", filename) as path:
#         return str(path)




def get_image_path(filename):
    """
    使用 importlib.resources 获取打包在包内的图片路径（推荐方式）
    """
    # 获取指向图片的 Traversable 对象
    resource = files('webot.images') / filename

    # 使用 as_file 上下文管理器，将资源转换为临时文件系统路径
    # 退出 with 块后，临时文件会被自动清理
    with as_file(resource) as path:
        # 返回 pathlib.Path 对象
        return str(path)

def main():
    logger.info("启动 Webot 微信机器人")

    # 1. 准备微信窗口
    resize_window(config.WECHAT_WINDOW_TITLE,
                  config.DEFAULT_WINDOW_WIDTH,
                  config.DEFAULT_WINDOW_HEIGHT)
    center_window(config.WECHAT_WINDOW_TITLE)
    activate_window(config.WECHAT_WINDOW_TITLE)

    # 点击联系人按钮
    # contacts sidebar
    contacts_path = get_image_path(config.BTN_CONTACTS_IMAGE)
    click_ui_element(contacts_path)

    # 2. 等待用户确认
    wait_for_user_focus(seconds=1, message="请确保微信聊天窗口已打开且可见")

    # 3. 搜索框输入联系人
    input_box_path = get_image_path(config.INPUT_SEARCH_CONTACT)
    success = find_and_input_text(
        image_path=input_box_path,
        text="口口",
        send_enter=True,
        confidence=config.CONFIDENCE_LEVEL
    )

    if not success:
        logger.error("消息发送失败，终止后续操作")
        return

    # 4. 后续操作示例（最大化窗口，滚动历史聊天记录并读取记录）
    import pyautogui
    # 1) 最大化窗口
    maximize_window("微信")
    wait_for_user_focus(seconds=1, message="请确保微信聊天窗口最大化")
    # 2) 清空输入框
    input_box_path = get_image_path(config.INPUT_MESSAGE_IN)
    clear_text_field(input_box_path)
    find_and_input_text(input_box_path, '浏览聊天历史记录...', send_enter=False)
    # 3）滚动400 pixels
    pyautogui.moveRel(0, -100, duration=0.5)
    delta_height = 10 # 400 pixels
    for idx in range(0, 5):
        scroll_repeatedly(times=delta_height, direction="up")    # times = 40 pixels
        pyautogui.screenshot(f'../../test/images/cap_{idx:03d}.png')

    logger.info("Webot 流程执行完毕")

if __name__ == "__main__":
    main()