#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 楚雄师范学院人工智能专业《自然语言处理》
# 微信Agent项目 PBL示例
# 主要解决微信界面激活和移动窗口、按图标定位、朋友圈点击和滚动操作、在微信聊天窗口发送或读取消息、在微信聊天窗口发送和接受文件（包含视频）的操作。
#   其中视频和文件操作涉及到定位微信界面上的某些面板位置，比如左边栏、联系人列表面板、聊条消息面板等，这些操作见t_bitwise.py。
#   还可以通过深度学习的模型训练，这个应该更加靠谱，但暂时还没有人做。
# 用到pyautogui，shutil，PyQT6
#
# Awen. 2026.7
#
# 致谢
#
# Copyright (C) 2025 Awen <lvyu@cxtc.edu.cn>
# Licensed under the GNU LGPL v2.1 - https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html

"""
Run with:
    python ./t_main.py
"""
  
import sys
import pyautogui
import shutil
from pathlib import Path
from PyQt6.QtCore import QUrl, QMimeData
from PyQt6.QtWidgets import QApplication

from webot.skills.click_skill import click_ui_element
from webot.skills.window_skill import activate_window
from webot.skills.scroll_skill import scroll_repeatedly
from webot.skills.cursor_pos_calculate_skill import calculate_cursor_position
from webot.utils import config
from webot.utils import get_logger, get_image_path


logger = get_logger(__name__)

def locate_and_move_cursor(image_name, confidence=config.CONFIDENCE_LEVEL, xoffset=0, yoffset=50):
    result = calculate_cursor_position(image_name, confidence=confidence)
    if result["found"]:
        pyautogui.moveTo(result["x"] + xoffset, result["y"] + yoffset)
        logger.info(f"已定位并移动到 {image_name} -> ({result['x'] + xoffset}, {result['y'] + yoffset})")
        return True
    else:
        logger.warning(f"未找到 {image_name}")
        return False

def scroll_wechat(direction="down", amount=30, times=10):
    # activate_window(config.WECHAT_WINDOW_TITLE, config.WECHAT_WINDOW_CLSNAME)
    scroll_repeatedly(amount=amount, times=times, direction=direction)
    logger.info(f"微信窗口已滚动 {direction} {amount}x{times}")

def click_first_post_menu_and_move_over_thumbs():
    result = calculate_cursor_position(get_image_path(config.IMG_POST))
    if result["found"]:
        pyautogui.moveTo(result["x"], result["y"])
        pyautogui.click(result["x"], result["y"])
        pyautogui.moveTo(result["x"] - 150, result["y"])
        logger.info(f"已定位{config.IMG_POST}，并移动到  -> ({result['x'] }, {result['y'] })")
        return (result["x"] - 150, result['y'])
    else:
        logger.warning(f"未找到 {config.IMG_POST}")
        return None

def set_file_to_clipboard_pyqt6(file_path: str):
    """使用 PyQt6 将文件路径以文件对象格式写入剪贴板"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    clipboard = app.clipboard()
    mime_data = QMimeData()
    url = QUrl.fromLocalFile(file_path)
    mime_data.setUrls([url])
    clipboard.setMimeData(mime_data)

def get_files_from_clipboard():
    """从剪贴板获取文件路径列表（仅支持文件，不含目录）"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    clipboard = app.clipboard()
    mime_data = clipboard.mimeData()
    # 检查是否包含文件 URL 列表
    if not mime_data.hasUrls():
        return []
    urls = mime_data.urls()
    file_paths = []
    for url in urls:
        # 仅处理本地文件
        if url.isLocalFile():
            path = url.toLocalFile()
            file_paths.append(path)
    return file_paths

def copy_files_from_clipboard(dest_dir="."):
    """将剪贴板中的文件复制到目标目录"""
    files = get_files_from_clipboard()
    if not files:
        print("剪贴板中没有文件。")
        return
    dest_path = Path(dest_dir)
    dest_path.mkdir(parents=True, exist_ok=True)
    for src in files:
        src_path = Path(src)
        if not src_path.is_file():
            print(f"跳过非文件: {src}")
            continue
        # 处理文件名冲突：若存在则添加序号
        dest_file = dest_path / src_path.name
        counter = 1
        while dest_file.exists():
            stem = src_path.stem
            suffix = src_path.suffix
            new_name = f"{stem}_{counter}{suffix}"
            dest_file = dest_path / new_name
            counter += 1
        try:
            shutil.copy2(src, dest_file)  # copy2 保留元数据
            print(f"已复制: {src} -> {dest_file}")
        except Exception as e:
            print(f"复制失败: {src} -> {dest_file}, 错误: {e}")


if __name__ == "__main__":
    # 1.激活微信窗口
    window_title = "微信"
    class_name = config.WECHAT_WINDOW_CLSNAME
    success = activate_window(config.WECHAT_WINDOW_TITLE, class_name)
    if success:
        logger.info("微信窗口已激活")
    else:
        logger.warning("未能激活微信窗口")
    # 2.激活朋友圈窗口
    click_ui_element(get_image_path(config.IMG_MOMENTS))
    window_title = "朋友圈"
    class_name = "MomentsQWindowIcon"
    success = activate_window(config.MOMENTS_WINDOW_TITLE, class_name)
    if success:
        logger.info("朋友圈窗口已激活")
    else:
        logger.warning("未能激活朋友圈窗口")
    # 3.定位点赞按钮，点赞和滚动
    for ii in range(2):
        (xx, yy) = click_first_post_menu_and_move_over_thumbs()
        logger.info(f'当前坐标：{yy}')
        pyautogui.moveTo(xx - 100, yy)
        rg = int(yy * 10 / 463)
        scroll_wechat(direction="down", times=rg)   

    activate_window(config.WECHAT_WINDOW_TITLE, class_name)
    test_file_path = r"E:\视频\ai-aided-english-reading.mp4"
    set_file_to_clipboard_pyqt6(test_file_path)
    pyautogui.hotkey('ctrl', 'v')
    input("pause")
    copy_files_from_clipboard('output')

    # 1.滚动;2.抓图;3.截图t_diff_pic;
    # if(locate_and_move_cursor(get_image_path(config.IMG_MOMENTS), confidence=config.CONFIDENCE_LEVEL)):
        # # 测试滚动微信窗口
        #     scroll_wechat(direction="up", amount=30, times=10)   