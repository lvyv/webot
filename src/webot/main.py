#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import json
import logging
import os

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QTextEdit, QLabel, QGroupBox, QCheckBox,
    QComboBox,
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont, QIcon

import pyautogui

from webot import config
from webot.skills import (
    resize_window, move_window, activate_window, click_ui_element,
    find_and_input_text,
    ClickUiElementSkill, InputTextSkill, FindAndInputTextSkill,
    ActivateWindowSkill, ResizeWindowSkill, MoveWindowSkill,
    ScrollRepeatedlySkill, WaitForUserFocusSkill,
    ReadChatHistorySkill, GetUnreadChatsSkill,
    ProcessChatSkill, SendReplySkill, ClickChatSkill,
)
from webot.agent import AgentLoop, Session, Memory, JsonLinesBackend, SkillManager, LLMClient
from webot.skills.recording_skill import RecordingManager
from webot.command_parser import CommandParser
from webot.utils import get_logger, get_image_path

logger = get_logger(__name__)

RULES_PATH = os.path.join(os.path.dirname(__file__), "rules.json")


def register_all_skills(mgr):
    mgr.register(ClickUiElementSkill())
    mgr.register(InputTextSkill())
    mgr.register(FindAndInputTextSkill())
    mgr.register(ActivateWindowSkill())
    mgr.register(ResizeWindowSkill())
    mgr.register(MoveWindowSkill())
    mgr.register(ScrollRepeatedlySkill())
    mgr.register(WaitForUserFocusSkill())
    mgr.register(ReadChatHistorySkill())
    mgr.register(GetUnreadChatsSkill())
    mgr.register(ProcessChatSkill())
    mgr.register(SendReplySkill())
    mgr.register(ClickChatSkill())


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
        self.setWindowTitle("Webot 助手")
        self.setWindowIcon(QIcon(get_image_path("webot.png")))
        self.setGeometry(100, 100, 640, 500)
        self.setWindowOpacity(0.85)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        self._cmd_parser = CommandParser()
        self._setup_commands()

        self._agent_running = False
        self._agent_timer = QTimer(self)

        self._init_agent()
        self._init_recording()
        self._setup_ui()
        self._agent_timer.timeout.connect(self._agent_tick)

    def _init_agent(self):
        self.session = Session()
        self.memory = Memory(backend=JsonLinesBackend())
        self.skill_mgr = SkillManager()
        register_all_skills(self.skill_mgr)
        self.llm_client = LLMClient()
        if not self.llm_client.available:
            logger.info("LLM 不可用，自动使用模板匹配模式")
        self.agent = AgentLoop(
            skill_manager=self.skill_mgr,
            memory=self.memory,
            session=self.session,
            llm_client=self.llm_client if self.llm_client.available else None,
        )

    def _init_recording(self):
        self.rec_mgr = RecordingManager(work_dir=os.getcwd())
        self.rec_mgr.start_listeners()
        self.rec_mgr.signals.log.connect(lambda msg: logger.info(msg))
        self.rec_mgr.signals.event_recorded.connect(self._on_record_event)

    def enterEvent(self, event):
        self.rec_mgr.enter_window()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.rec_mgr.leave_window()
        super().leaveEvent(event)

    def closeEvent(self, event):
        self.rec_mgr.stop_listeners()
        super().closeEvent(event)

    def _on_record_event(self, evt):
        self.record_edit.append(json.dumps(evt, ensure_ascii=False))
        cursor = self.record_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.record_edit.setTextCursor(cursor)

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

        self._setup_agent_panel(layout)
        layout.addSpacing(8)
        self._setup_recording_panel(layout)
        layout.addSpacing(8)
        self._setup_command_panel(layout)
        layout.addSpacing(8)
        self._setup_log_panel(layout)

        webot_logger = logging.getLogger('webot')
        webot_logger.setLevel(logging.INFO)
        webot_logger.addHandler(QTextEditHandler(self.log_output))

    def _setup_agent_panel(self, parent_layout):
        group = QGroupBox("Agent 监控")
        layout = QVBoxLayout(group)

        btn_row = QHBoxLayout()
        self.btn_side = QPushButton("并排显示微信")
        self.btn_side.setMinimumHeight(32)
        self.btn_side.clicked.connect(self._side_by_side)
        btn_row.addWidget(self.btn_side)

        self.btn_agent_start = QPushButton("开始监控")
        self.btn_agent_start.setMinimumHeight(32)
        self.btn_agent_start.clicked.connect(self._start_agent)
        btn_row.addWidget(self.btn_agent_start)

        self.btn_agent_stop = QPushButton("停止监控")
        self.btn_agent_stop.setMinimumHeight(32)
        self.btn_agent_stop.setEnabled(False)
        self.btn_agent_stop.clicked.connect(self._stop_agent)
        btn_row.addWidget(self.btn_agent_stop)

        layout.addLayout(btn_row)

        status_row = QHBoxLayout()
        self.lbl_agent_status = QLabel("状态: 已停止")
        self.lbl_agent_status.setStyleSheet("color: gray; font-weight: bold;")
        status_row.addWidget(self.lbl_agent_status)

        self.lbl_unread_count = QLabel("未读: 0")
        status_row.addWidget(self.lbl_unread_count)

        self.lbl_processed_count = QLabel("已处理: 0")
        status_row.addWidget(self.lbl_processed_count)

        self.chk_auto_reply = QCheckBox("自动回复已启用")
        self.chk_auto_reply.setChecked(True)
        self.chk_auto_reply.toggled.connect(self._on_auto_reply_toggled)
        status_row.addWidget(self.chk_auto_reply)

        self.cmb_reply_mode = QComboBox()
        self.cmb_reply_mode.addItems(["模板匹配", "LLM 智能回复", "LLM + 模板降级"])
        self.cmb_reply_mode.currentIndexChanged.connect(self._on_reply_mode_changed)
        status_row.addWidget(self.cmb_reply_mode)

        layout.addLayout(status_row)

        self.lbl_agent_detail = QLabel("")
        self.lbl_agent_detail.setWordWrap(True)
        layout.addWidget(self.lbl_agent_detail)

        parent_layout.addWidget(group)

    def _setup_recording_panel(self, parent_layout):
        group = QGroupBox("操作录制")
        layout = QVBoxLayout(group)

        slot_row = QHBoxLayout()
        slot_row.addWidget(QLabel("槽位:"))
        self.slot_buttons = []
        for i in range(1, 11):
            btn = QPushButton(str(i))
            btn.setFixedSize(30, 30)
            slot = i
            btn.clicked.connect(lambda checked, n=slot: self._on_slot_click(n))
            slot_row.addWidget(btn)
            self.slot_buttons.append(btn)
        layout.addLayout(slot_row)

        ctrl_row = QHBoxLayout()
        self.btn_record = QPushButton("录制")
        self.btn_record.clicked.connect(self._on_record_click)
        ctrl_row.addWidget(self.btn_record)

        self.btn_stop = QPushButton("停止录制")
        self.btn_stop.clicked.connect(self._on_stop_click)
        ctrl_row.addWidget(self.btn_stop)

        ctrl_row.addStretch()

        self.btn_activate_wx = QPushButton("激活微信")
        self.btn_activate_wx.clicked.connect(self._activate_wechat)
        ctrl_row.addWidget(self.btn_activate_wx)

        self.btn_min_wx = QPushButton("最小化微信")
        self.btn_min_wx.clicked.connect(self._minimize_wechat)
        ctrl_row.addWidget(self.btn_min_wx)

        layout.addLayout(ctrl_row)

        self.record_edit = QTextEdit()
        self.record_edit.setReadOnly(True)
        self.record_edit.setMaximumHeight(80)
        self.record_edit.setFont(QFont("Consolas", 8))
        layout.addWidget(self.record_edit)

        parent_layout.addWidget(group)

    def _on_slot_click(self, num):
        self.rec_mgr.select_slot(num)
        for i, btn in enumerate(self.slot_buttons, 1):
            btn.setStyleSheet("background-color: #2196F3; color: white;" if i == num else "")
        if self.rec_mgr.recording_state not in ("armed", "recording"):
            self.rec_mgr.replay_slot(num)

    def _on_record_click(self):
        self.rec_mgr.arm_recording()

    def _on_stop_click(self):
        self.rec_mgr.disarm_recording()
        for btn in self.slot_buttons:
            btn.setStyleSheet("")

    @staticmethod
    def _activate_wechat():
        import ctypes
        import pygetwindow as gw
        try:
            windows = gw.getWindowsWithTitle("微信")
            if not windows:
                CLASS_NAME = "Qt51514QWindowIcon"
                user32 = ctypes.windll.user32
                hwnd = user32.FindWindowW(CLASS_NAME, None)
                if not hwnd:
                    logger.warning("未找到微信窗口")
                    return
            else:
                hwnd = windows[0]._hWnd
            user32 = ctypes.windll.user32
            user32.ShowWindow(hwnd, 3)
            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)
            logger.info("已激活微信")
        except Exception as e:
            logger.error(f"激活微信失败: {e}")

    @staticmethod
    def _minimize_wechat():
        import pygetwindow as gw
        try:
            windows = gw.getWindowsWithTitle("微信")
            if windows:
                windows[0].minimize()
                logger.info("已最小化微信")
        except Exception as e:
            logger.error(f"最小化微信失败: {e}")

    def _setup_command_panel(self, parent_layout):
        parent_layout.addWidget(QLabel("指令输入 (Enter 执行):"))
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(
            "/contact:张三  或   /张三：你好  或   /rules 打开规则文件"
        )
        self.input_field.returnPressed.connect(self._execute_command)
        parent_layout.addWidget(self.input_field)

    def _setup_log_panel(self, parent_layout):
        parent_layout.addWidget(QLabel("操作日志:"))
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont("Consolas", 9))
        parent_layout.addWidget(self.log_output)

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
        text = self.input_field.text().strip()
        if not text:
            return

        if text == "/rules":
            self._open_rules_file()
            self.input_field.clear()
            return

        if not text.startswith("/"):
            logger.warning(f"指令必须以 / 开头: {text}")
            self.input_field.clear()
            return
        success = self._cmd_parser.execute(text)
        if not success:
            logger.warning(f"无法识别的指令: {text}")
        self.input_field.clear()

    def _open_rules_file(self):
        path = RULES_PATH
        if not os.path.exists(path):
            from webot.skills.auto_reply_skill import save_default_rules
            save_default_rules(path)
        os.startfile(path)
        logger.info(f"已打开规则文件: {path}")

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

    def _on_auto_reply_toggled(self, checked):
        self.agent.auto_reply_enabled = checked

    def _on_reply_mode_changed(self, idx):
        mode_map = {0: "template", 1: "llm", 2: "llm_with_fallback"}
        self.agent.reply_mode = mode_map.get(idx, "template")
        logger.info(f"回复模式切换为: {self.agent.reply_mode}")

    def _start_agent(self):
        if self._agent_running:
            return
        self._agent_running = True
        self.agent.reset()

        self.btn_agent_start.setEnabled(False)
        self.btn_agent_stop.setEnabled(True)
        self.lbl_agent_status.setText("状态: 运行中")
        self.lbl_agent_status.setStyleSheet("color: green; font-weight: bold;")
        self.lbl_unread_count.setText("未读: 0")
        self.lbl_processed_count.setText("已处理: 0")
        self.lbl_agent_detail.setText("")

        self.agent.reload_rules()
        self._on_auto_reply_toggled(self.chk_auto_reply.isChecked())
        self._on_reply_mode_changed(self.cmb_reply_mode.currentIndex())

        logger.info("Agent 监控已启动")
        self._agent_timer.start(int(config.AGENT_POLL_INTERVAL * 1000))

    def _stop_agent(self):
        if not self._agent_running:
            return
        self._agent_running = False
        self._agent_timer.stop()

        self.btn_agent_start.setEnabled(True)
        self.btn_agent_stop.setEnabled(False)
        self.lbl_agent_status.setText("状态: 已停止")
        self.lbl_agent_status.setStyleSheet("color: gray; font-weight: bold;")
        logger.info("Agent 监控已停止")

    def _agent_tick(self):
        if not self._agent_running:
            return

        unreads, processed = self.agent.tick()

        self.lbl_unread_count.setText(f"未读: {len(unreads)}")
        self.lbl_processed_count.setText(f"已处理: {processed}")

        detail_lines = []
        for m in unreads:
            name = m["chat_name"]
            preview = m.get("preview", "")
            detail_lines.append(f"  · {name}: {preview or '(无预览)'}")

        if detail_lines:
            self.lbl_agent_detail.setText("\n".join(detail_lines))
        else:
            self.lbl_agent_detail.setText("")


def main():
    app = QApplication(sys.argv)
    window = WebotWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
