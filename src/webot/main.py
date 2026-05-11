#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import logging
from importlib.resources import files, as_file

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QLineEdit, QTextEdit, QLabel,
)
from PyQt6.QtGui import QFont

import pyautogui

from webot import config
from webot.skills import (
    resize_window, move_window, activate_window, click_ui_element,
    find_and_input_text,
)
from webot.command_parser import CommandParser
from webot.utils import get_logger

logger = get_logger(__name__)


def get_image_path(filename):
    resource = files('webot.images') / filename
    with as_file(resource) as path:
        return str(path)


class QTextEditHandler(logging.Handler):
    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit
        self.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S',
        ))

    def emit(self, record):
        msg = self.format(record)
        self.text_edit.append(msg)


class WebotWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Webot 微信助手")
        self.setMinimumSize(600, 400)

        self._cmd_parser = CommandParser()
        self._setup_commands()
        self._setup_ui()

    def _setup_commands(self):
        self._cmd_parser.register(
            "search_contact",
            r'^/contact:(.+)$',
            self._handle_search_contact,
        )
        self._cmd_parser.register(
            "send_message",
            r'^/([^：]+)：(.*)$',
            self._handle_send_message,
        )

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.btn_side = QPushButton("并排显示微信")
        self.btn_side.setMinimumHeight(36)
        self.btn_side.clicked.connect(self._side_by_side)
        layout.addWidget(self.btn_side)

        layout.addSpacing(8)
        layout.addWidget(QLabel("指令输入 (Enter 执行):"))

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(
            "/contact:张三  或   /张三：你好"
        )
        self.input_field.returnPressed.connect(self._execute_command)
        layout.addWidget(self.input_field)

        layout.addSpacing(8)
        layout.addWidget(QLabel("操作日志:"))

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log_output)

        handler = QTextEditHandler(self.log_output)
        logging.getLogger('webot').addHandler(handler)

    def _side_by_side(self):
        screen_w, screen_h = pyautogui.size()
        half_w = screen_w // 2

        resize_window(config.WECHAT_WINDOW_TITLE, half_w, screen_h)
        move_window(config.WECHAT_WINDOW_TITLE, 0, 0)

        self.move(half_w, 0)
        self.resize(half_w, screen_h)

        activate_window(config.WECHAT_WINDOW_TITLE)
        logger.info("并排显示完成：微信左屏 | Webot 右屏")

    def _execute_command(self):
        text = self.input_field.text()
        if not text.startswith("/"):
            logger.warning(f"指令必须以 / 开头: {text}")
            self.input_field.clear()
            return
        success = self._cmd_parser.execute(text)
        if not success:
            logger.warning(f"无法识别的指令: {text}")
        self.input_field.clear()

    def _handle_search_contact(self, name):
        name = name.strip()
        logger.info(f"执行命令：搜索联系人 [{name}]")
        activate_window(config.WECHAT_WINDOW_TITLE)
        click_ui_element(get_image_path(config.BTN_CONTACTS_IMAGE))
        find_and_input_text(
            get_image_path(config.INPUT_SEARCH_CONTACT),
            name, send_enter=True,
        )
        logger.info(f"联系人 [{name}] 已搜索并打开")

    def _handle_send_message(self, contact, message):
        contact = contact.strip()
        message = message.strip()
        logger.info(f"执行命令：向 [{contact}] 发送消息")
        activate_window(config.WECHAT_WINDOW_TITLE)
        click_ui_element(get_image_path(config.BTN_CONTACTS_IMAGE))
        find_and_input_text(
            get_image_path(config.INPUT_SEARCH_CONTACT),
            contact, send_enter=True,
        )
        find_and_input_text(
            get_image_path(config.INPUT_MESSAGE_IN),
            message, send_enter=True,
        )
        logger.info(f"已向 [{contact}] 发送消息")


def main():
    app = QApplication(sys.argv)
    window = WebotWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
