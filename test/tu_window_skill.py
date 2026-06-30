"""Unit tests for window_skill.activate_window."""

from unittest.mock import MagicMock, patch
from webot import config
from webot.skills.window_skill import activate_window
import subprocess
import time
import pytest


@pytest.mark.integration
class TestActivateWindowIntegration:
    """集成测试 — 真实调用 pygetwindow，不 mock"""

    def test_wechat_window_found_returns_true(self):
        result = activate_window(config.WECHAT_WINDOW_TITLE, config.WECHAT_WINDOW_CLSNAME)
        assert result is True

    def test_wechat_window_not_found_returns_true(self):
        result = activate_window('__这一看就不存在的窗口_9527__', config.WECHAT_WINDOW_CLSNAME)
        assert result is True

    def test_window_not_found_returns_false(self):
        result = activate_window("__这一看就不存在的窗口_2947__", "abc")
        assert result is False

    # def test_activate_real_notepad(self):
    #     """启动记事本 → 激活它 → 断言成功"""
    #     proc = subprocess.Popen(["notepad.exe"])
    #     try:
    #         time.sleep(1)
    #         result = activate_window("无标题 - 记事本", config.WECHAT_WINDOW_CLSNAME)
    #         assert result is True
    #     finally:
    #         proc.kill()
    #         proc.wait()