import sys
import json
import time
import threading
import ctypes
import ctypes.wintypes
from PyQt6.QtWidgets import QApplication, QMainWindow, QTextEdit, QVBoxLayout, QHBoxLayout, QWidget, QPushButton
from PyQt6.QtCore import pyqtSignal, QObject, Qt
from pynput import mouse, keyboard
from pynput.mouse import Button as MouseButton
from pynput.keyboard import Key as KbdKey, KeyCode
import pygetwindow as gw


class EventSignals(QObject):
    mouse_keyboard_evt = pyqtSignal(str)
    recording_evt = pyqtSignal(dict)
    replay_log = pyqtSignal(str)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("鼠标/键盘监听 + Qt6 窗口")
        self.setGeometry(100, 100, 360, 240)
        self.setWindowOpacity(0.60)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        # 录制 & 回放状态
        self.recording_state = "idle"
        self.target_slot = None
        self.recorded_events = []
        self.mouse_in_window = True
        self._replaying = False

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 并排放置两个文本区域
        text_layout = QHBoxLayout()
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.record_edit = QTextEdit()
        self.record_edit.setReadOnly(False)
        text_layout.addWidget(self.text_edit)
        text_layout.addWidget(self.record_edit)
        layout.addLayout(text_layout)

        # 第一排按钮
        button_layout = QHBoxLayout()
        self.activate_btn = QPushButton("激活微信")
        self.minimize_btn = QPushButton("最小化微信")
        self.activate_moments_btn = QPushButton("激活朋友圈")

        self.activate_btn.clicked.connect(self.activate_wechat)
        self.minimize_btn.clicked.connect(self.minimize_wechat)
        self.activate_moments_btn.clicked.connect(self.activate_moments)
        button_layout.addWidget(self.activate_btn)
        button_layout.addWidget(self.minimize_btn)
        button_layout.addWidget(self.activate_moments_btn)
        layout.addLayout(button_layout)

        # 12 个方形数字按钮
        number_layout = QHBoxLayout()
        self.number_buttons = []
        for i in range(1, 11):
            btn = QPushButton(str(i))
            btn.setFixedSize(32, 32)
            slot = i
            btn.clicked.connect(lambda checked, n=slot: self.on_number_click(n))
            number_layout.addWidget(btn)
            self.number_buttons.append(btn)
        layout.addLayout(number_layout)

        # 录制 / 停止录制
        record_layout = QHBoxLayout()
        self.record_btn = QPushButton("录制")
        self.stop_btn = QPushButton("停止录制")
        self.record_btn.clicked.connect(self.on_record_click)
        self.stop_btn.clicked.connect(self.on_stop_click)
        record_layout.addWidget(self.record_btn)
        record_layout.addWidget(self.stop_btn)
        layout.addLayout(record_layout)

        self.signals = EventSignals()
        self.signals.mouse_keyboard_evt.connect(self.append_text)
        self.signals.recording_evt.connect(self.on_recording_event)
        self.signals.replay_log.connect(self.append_text)

        self.start_listeners()

    # ==================== 监听器 ====================
    def start_listeners(self):
        self.mouse_listener = mouse.Listener(
            on_move=self.on_mouse_move,
            on_click=self.on_mouse_click,
            on_scroll=self.on_mouse_scroll
        )
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_key_press,
            on_release=self.on_key_release
        )
        self.mouse_listener.start()
        self.keyboard_listener.start()

    # ==================== 录制逻辑 ====================

    def on_record_click(self):
        self.recording_state = "armed"
        self.target_slot = None
        self.recorded_events = []
        for btn in self.number_buttons:
            btn.setStyleSheet("")
        self.append_text("[录制] 请点击数字按钮选择槽位，然后鼠标移出窗口开始录制")

    def on_stop_click(self):
        if self.recording_state == "recording" and self.mouse_in_window:
            self.stop_recording()
        elif self.recording_state == "armed":
            self.recording_state = "idle"
            self.target_slot = None
            self.recorded_events = []
            self.record_edit.clear()
            for btn in self.number_buttons:
                btn.setStyleSheet("")
            self.append_text("[录制] 已取消")
        else:
            self.append_text("[录制] 当前没有进行中的录制")

    def enterEvent(self, event):
        self.mouse_in_window = True
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.mouse_in_window = False
        if self.recording_state == "armed":
            if self.target_slot is None:
                self.append_text("[录制] 请先选择一个数字按钮再移出窗口")
            else:
                self.start_recording()
        super().leaveEvent(event)

    def start_recording(self):
        self.recording_state = "recording"
        self.recorded_events = []
        self.record_edit.clear()
        self.append_text(f"[录制] 开始录制 → 槽位 {self.target_slot}")

    def stop_recording(self):
        # 从可编辑控件 record_edit 中解析每一行 JSON
        events = []
        text = self.record_edit.toPlainText()
        for line in text.strip().split("\n"):
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    self.append_text(f"[录制] 跳过无法解析的行: {line[:60]}")
        self.recorded_events = events

        filename = f"{self.target_slot}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=2)

        self.recording_state = "idle"
        for btn in self.number_buttons:
            btn.setStyleSheet("")
        self.append_text(f"[录制] 已停止，保存至 {filename}，共 {len(events)} 条事件")

    # ==================== 回放逻辑 ====================

    def on_number_click(self, num):
        self.target_slot = num

        for i, btn in enumerate(self.number_buttons, 1):
            if i == num:
                btn.setStyleSheet("background-color: #2196F3; color: white;")
            else:
                btn.setStyleSheet("")

        if self.recording_state in ("armed", "recording"):
            self.append_text(f"[录制] 目标槽位: {num}")
            return

        filename = f"{num}.json"
        try:
            with open(filename, "r", encoding="utf-8") as f:
                events = json.load(f)
        except FileNotFoundError:
            self.append_text(f"[回放] {filename} 不存在，无录制数据")
            return
        except json.JSONDecodeError:
            self.append_text(f"[回放] {filename} 格式错误")
            return

        if self._replaying:
            self.append_text("[回放] 正在回放中，请等待完成")
            return

        self.append_text(f"[回放] 开始回放 {filename}，共 {len(events)} 条事件")
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
                    self.signals.replay_log.emit(f"[回放] 第 {i + 1} 条执行出错: {e}")
                time.sleep(0.03)
        finally:
            self._replaying = False
            self.signals.replay_log.emit(f"[回放] 回放完成，共执行 {len(events)} 条")


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
        # 先查特殊键 (如 Key.space, Key.enter...)
        if s.startswith("Key."):
            name = s[4:]
            for attr_name in dir(KbdKey):
                if not attr_name.startswith("_"):
                    if attr_name == name:
                        return getattr(KbdKey, attr_name)
        # 普通字符键
        try:
            return KeyCode.from_char(s)
        except Exception:
            return KbdKey.unknown
    
    # 1. 底层API热键函数
    @staticmethod
    def send_hotkey():
        VK_CONTROL, VK_MENU, VK_W = 0x11, 0x12, 0x57
        KEYEVENTF_KEYUP = 0x2
        user32 = ctypes.windll.user32
        keybd_event = user32.keybd_event

        for vk in [VK_CONTROL, VK_MENU]:
            keybd_event(vk, 0, 0, 0)
        time.sleep(0.05)  # 小延迟，提高成功率
        keybd_event(VK_W, 0, 0, 0)
        keybd_event(VK_W, 0, KEYEVENTF_KEYUP, 0)
        for vk in [VK_MENU, VK_CONTROL]:
            keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)

    @staticmethod
    def find_window_by_class(class_name):
        """通过类名查找窗口，返回窗口句柄（HWND）。"""
        # 加载 user32.dll
        user32 = ctypes.windll.user32
        # 定义参数类型和返回值类型（可选，但有助于避免错误）
        user32.FindWindowW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
        user32.FindWindowW.restype = ctypes.c_void_p  # 返回 HWND
        user32.IsIconic.argtypes = [ctypes.c_void_p]
        user32.IsIconic.restype = ctypes.c_bool
        hwnd = user32.FindWindowW(class_name, None)  # 第二个参数为窗口标题，None 表示忽略
        if hwnd is None or hwnd == 0:
            print(f"未找到类名为 '{class_name}' 的窗口")
            return None
        print(f"找到窗口，句柄: {hwnd}")
        return hwnd

    # ==================== 事件回调（非主线程 → 信号 → 主线程）====================

    def on_recording_event(self, event_dict):
        self.recorded_events.append(event_dict)
        # record_edit 中每行存一个紧凑 JSON 对象
        line = json.dumps(event_dict, ensure_ascii=False)
        self.record_edit.append(line)
        cursor = self.record_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.record_edit.setTextCursor(cursor)

    def on_mouse_move(self, x, y):
        self.signals.mouse_keyboard_evt.emit(f"[鼠标移动] ({x}, {y})")
        if self.recording_state == "recording" and not self.mouse_in_window:
            self.signals.recording_evt.emit({"type": "mouse_move", "x": x, "y": y})

    def on_mouse_click(self, x, y, button, pressed):
        action = "按下" if pressed else "释放"
        self.signals.mouse_keyboard_evt.emit(f"[鼠标{action}] {button} 于 ({x}, {y})")
        if self.recording_state == "recording" and not self.mouse_in_window:
            self.signals.recording_evt.emit({
                "type": "mouse_click", "x": x, "y": y,
                "button": str(button), "pressed": pressed
            })

    def on_mouse_scroll(self, x, y, dx, dy):
        self.signals.mouse_keyboard_evt.emit(f"[鼠标滚动] 于 ({x}, {y}) 偏移 ({dx}, {dy})")
        if self.recording_state == "recording" and not self.mouse_in_window:
            self.signals.recording_evt.emit({
                "type": "mouse_scroll", "x": x, "y": y, "dx": dx, "dy": dy
            })

    def on_key_press(self, key):
        try:
            k = key.char
        except AttributeError:
            k = str(key)
        self.signals.mouse_keyboard_evt.emit(f"[键盘按下] {k}")
        if self.recording_state == "recording" and not self.mouse_in_window:
            self.signals.recording_evt.emit({"type": "key_press", "key": k})

    def on_key_release(self, key):
        try:
            k = key.char
        except AttributeError:
            k = str(key)
        self.signals.mouse_keyboard_evt.emit(f"[键盘释放] {k}")
        if self.recording_state == "recording" and not self.mouse_in_window:
            self.signals.recording_evt.emit({"type": "key_release", "key": k})
    # ==================== UI 辅助 ====================

    def append_text(self, text):
        self.text_edit.append(text)
        cursor = self.text_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.text_edit.setTextCursor(cursor)

    def activate_moments(self):
        try:
            windows = gw.getWindowsWithTitle('朋友圈')
            if not windows:
                self.append_text("[信息] 未找到朋友圈窗口")
                return
            hwnd = windows[0]._hWnd
            user32 = ctypes.windll.user32
            user32.ShowWindow(hwnd, 9)
            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)
            # windows[0].maximize()
        except Exception as e:
            self.append_text(f"[错误] 激活朋友圈失败: {e}")

    def activate_wechat(self):
        try:
            windows = gw.getWindowsWithTitle('微信')
            if not windows:
                # 要查找的窗口类名（微信主窗口类名）
                CLASS_NAME = "Qt51514QWindowIcon"
                # 使用示例
                hwnd = self.find_window_by_class(CLASS_NAME)
                if hwnd is None:
                    self.append_text("[信息] 未找到微信窗口")
                    return
                else:
                    self.send_hotkey()
            else:
                hwnd = windows[0]._hWnd
            user32 = ctypes.windll.user32
            user32.ShowWindow(hwnd, 3)
            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)
        except Exception as e:
            self.append_text(f"[错误] 激活微信失败: {e}")

    def minimize_wechat(self):
        try:
            windows = gw.getWindowsWithTitle('微信')
            if windows:
                windows[0].minimize()
            else:
                self.append_text("[信息] 未找到微信窗口")
        except Exception as e:
            self.append_text(f"[错误] 最小化微信失败: {e}")

    def closeEvent(self, event):
        self._replaying = False
        self.mouse_listener.stop()
        self.keyboard_listener.stop()
        self.mouse_listener.join()
        self.keyboard_listener.join()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
