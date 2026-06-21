import json
import os
import time
import threading

from PyQt6.QtCore import pyqtSignal, QObject
from pynput import mouse, keyboard
from pynput.mouse import Button as MouseButton
from pynput.keyboard import Key as KbdKey, KeyCode

from ..utils import get_logger

logger = get_logger(__name__)


class RecordingSignals(QObject):
    log = pyqtSignal(str)
    event_recorded = pyqtSignal(dict)


class RecordingManager:
    def __init__(self, work_dir="."):
        self.work_dir = work_dir
        self.recording_state = "idle"
        self.target_slot = None
        self._events = []
        self.mouse_in_window = True
        self._replaying = False
        self.signals = RecordingSignals()

        self.mouse_listener = None
        self.keyboard_listener = None

    def start_listeners(self):
        self.mouse_listener = mouse.Listener(
            on_move=self.on_mouse_move,
            on_click=self.on_mouse_click,
            on_scroll=self.on_mouse_scroll,
        )
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_key_press,
            on_release=self.on_key_release,
        )
        self.mouse_listener.start()
        self.keyboard_listener.start()
        logger.info("录制监听器已启动")

    def stop_listeners(self):
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.join()
        if self.keyboard_listener:
            self.keyboard_listener.join()
        logger.info("录制监听器已停止")

    # ==================== 录制控制 ====================

    def enter_window(self):
        self.mouse_in_window = True

    def leave_window(self):
        self.mouse_in_window = False
        if self.recording_state == "armed":
            if self.target_slot is None:
                self.signals.log.emit("[录制] 请先选择一个数字按钮再移出窗口")
            else:
                self._start_recording()

    def arm_recording(self):
        self.recording_state = "armed"
        self.target_slot = None
        self._events = []
        self.signals.log.emit("[录制] 请点击数字按钮选择槽位，然后鼠标移出窗口开始录制")

    def disarm_recording(self):
        if self.recording_state == "recording" and self.mouse_in_window:
            self._stop_recording()
        elif self.recording_state == "armed":
            self.recording_state = "idle"
            self.target_slot = None
            self._events = []
            self.signals.log.emit("[录制] 已取消")
        else:
            self.signals.log.emit("[录制] 当前没有进行中的录制")

    def select_slot(self, num):
        self.target_slot = num
        if self.recording_state in ("armed", "recording"):
            self.signals.log.emit(f"[录制] 目标槽位: {num}")

    def _start_recording(self):
        self.recording_state = "recording"
        self._events = []
        self.signals.log.emit(f"[录制] 开始录制 \u2192 槽位 {self.target_slot}")

    def _stop_recording(self):
        events = list(self._events)
        self._events = events
        filename = f"{self.target_slot}.json"
        filepath = os.path.join(self.work_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
        self.recording_state = "idle"
        self.signals.log.emit(f"[录制] 已停止，保存至 {filename}，共 {len(events)} 条事件")

    # ==================== 回放 ====================

    def replay_slot(self, num):
        if self._replaying:
            self.signals.log.emit("[回放] 正在回放中，请等待完成")
            return

        filename = f"{num}.json"
        filepath = os.path.join(self.work_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                events = json.load(f)
        except FileNotFoundError:
            self.signals.log.emit(f"[回放] {filename} 不存在，无录制数据")
            return
        except json.JSONDecodeError:
            self.signals.log.emit(f"[回放] {filename} 格式错误")
            return

        self.signals.log.emit(f"[回放] 开始回放 {filename}，共 {len(events)} 条事件")
        self._replaying = True
        t = threading.Thread(target=self._replay_task, args=(events,), daemon=True)
        t.start()

    def _replay_task(self, events):
        mc = mouse.Controller()
        kc = keyboard.Controller()
        try:
            for i, evt in enumerate(events):
                if not self._replaying:
                    break
                try:
                    t = evt["type"]
                    if t == "mouse_move":
                        mc.position = (evt["x"], evt["y"])
                    elif t == "mouse_click":
                        btn = self._parse_button(evt["button"])
                        if evt["pressed"]:
                            mc.press(btn)
                        else:
                            mc.release(btn)
                    elif t == "mouse_scroll":
                        mc.scroll(evt["dx"], evt["dy"])
                    elif t == "key_press":
                        kc.press(self._parse_key(evt["key"]))
                    elif t == "key_release":
                        kc.release(self._parse_key(evt["key"]))
                except Exception as e:
                    self.signals.log.emit(f"[回放] 第 {i+1} 条执行出错: {e}")
                time.sleep(0.03)
        finally:
            self._replaying = False
            self.signals.log.emit(f"[回放] 回放完成，共执行 {len(events)} 条")

    # ==================== 事件回调 ====================

    def _record_event(self, evt):
        self._events.append(evt)
        self.signals.event_recorded.emit(evt)

    def on_mouse_move(self, x, y):
        if self.recording_state == "recording" and not self.mouse_in_window:
            self._record_event({"type": "mouse_move", "x": x, "y": y})

    def on_mouse_click(self, x, y, button, pressed):
        if self.recording_state == "recording" and not self.mouse_in_window:
            self._record_event({
                "type": "mouse_click", "x": x, "y": y,
                "button": str(button), "pressed": pressed,
            })

    def on_mouse_scroll(self, x, y, dx, dy):
        if self.recording_state == "recording" and not self.mouse_in_window:
            self._record_event({
                "type": "mouse_scroll", "x": x, "y": y, "dx": dx, "dy": dy,
            })

    def on_key_press(self, key):
        try:
            k = key.char
        except AttributeError:
            k = str(key)
        if self.recording_state == "recording" and not self.mouse_in_window:
            self._record_event({"type": "key_press", "key": k})

    def on_key_release(self, key):
        try:
            k = key.char
        except AttributeError:
            k = str(key)
        if self.recording_state == "recording" and not self.mouse_in_window:
            self._record_event({"type": "key_release", "key": k})

    # ==================== 辅助 ====================

    @staticmethod
    def _parse_button(s):
        table = {
            "Button.left": MouseButton.left,
            "Button.right": MouseButton.right,
            "Button.middle": MouseButton.middle,
        }
        return table.get(s, MouseButton.left)

    @staticmethod
    def _parse_key(s):
        if s.startswith("Key."):
            name = s[4:]
            for attr_name in dir(KbdKey):
                if not attr_name.startswith("_") and attr_name == name:
                    return getattr(KbdKey, attr_name)
        try:
            return KeyCode.from_char(s)
        except Exception:
            return KbdKey.unknown
