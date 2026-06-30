from .click_skill import click_ui_element, ClickUiElementSkill
from .input_skill import clear_text_field, input_text, find_and_input_text, InputTextSkill, FindAndInputTextSkill
from .window_skill import activate_window, resize_window, maximize_window, center_window, move_window
from .window_skill import ActivateWindowSkill, ResizeWindowSkill, MoveWindowSkill
from .scroll_skill import scroll_page, scroll_repeatedly, ScrollRepeatedlySkill
from .wait_skill import wait_for_user_focus, WaitForUserFocusSkill
from .chat_ocr_skill import read_chat_history, ReadChatHistorySkill
from .reddot_skill import get_unread_chats, GetUnreadChatsSkill
from .auto_reply_skill import (
    load_rules, should_auto_reply, process_chat, auto_reply_cycle,
    select_reply, click_chat_by_position, read_chat_area, send_reply,
    find_file_helper_y, send_confirm_request,
    ProcessChatSkill, SendReplySkill, ClickChatSkill,
)
from .cursor_pos_calculate_skill import calculate_cursor_position, CalculateCursorPositionSkill
from .base import Skill
from ..agent.skill_manager import SkillManager

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

__all__ = [
    "click_ui_element", "ClickUiElementSkill",
    "clear_text_field", "input_text", "find_and_input_text", "InputTextSkill", "FindAndInputTextSkill",
    "activate_window", "resize_window", "maximize_window", "center_window", "move_window",
    "ActivateWindowSkill", "ResizeWindowSkill", "MoveWindowSkill",
    "scroll_page", "scroll_repeatedly", "ScrollRepeatedlySkill",
    "wait_for_user_focus", "WaitForUserFocusSkill",
    "read_chat_history", "ReadChatHistorySkill",
    "get_unread_chats", "GetUnreadChatsSkill",
    "load_rules", "should_auto_reply", "process_chat", "auto_reply_cycle",
    "select_reply", "click_chat_by_position", "read_chat_area", "send_reply",
    "find_file_helper_y", "send_confirm_request",
    "ProcessChatSkill", "SendReplySkill", "ClickChatSkill",
    "calculate_cursor_position", "CalculateCursorPositionSkill",
    "Skill", "register_all_skills",
]