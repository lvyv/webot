import sys
import time
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton


class TimerWindow(QWidget):
    """带定时器的窗口，能发送时间更新信号"""
    time_updated = pyqtSignal(str)  # 时间更新信号
    
    def __init__(self, window_title="定时器"):
        super().__init__()
        self.setWindowTitle(window_title)
        self.setGeometry(300, 300, 300, 150)
        
        layout = QVBoxLayout()
        
        self.label = QLabel("未启动")
        layout.addWidget(self.label)
        
        self.btn = QPushButton("启动定时器")
        self.btn.clicked.connect(self.toggle_timer)
        layout.addWidget(self.btn)
        
        self.setLayout(layout)
        
        # 定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.is_running = False
    
    def toggle_timer(self):
        """切换定时器状态"""
        if self.is_running:
            self.timer.stop()
            self.btn.setText("启动定时器")
            self.label.setText("定时器已停止")
            self.is_running = False
        else:
            self.timer.start(1000)
            self.btn.setText("停止定时器")
            self.label.setText("定时器运行中...")
            self.is_running = True
    
    def update_time(self):
        """更新时间并发射信号"""
        current_time = time.strftime('%H:%M:%S')
        self.label.setText(f"当前时间: {current_time}")
        self.time_updated.emit(current_time)  # 发射时间信号


class ReceiverWindow(QWidget):
    """接收时间更新的窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("时间接收器")
        self.setGeometry(350, 350, 300, 100)
        
        layout = QVBoxLayout()
        self.label = QLabel("等待接收时间...")
        layout.addWidget(self.label)
        self.setLayout(layout)
    
    def update_time_display(self, time_str):
        """接收并显示时间"""
        self.label.setText(f"收到时间: {time_str}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 创建窗口
    timer_window = TimerWindow("定时器发射器")
    receiver_window = ReceiverWindow()
    receiver_window2 = ReceiverWindow()
    receiver_window3 = ReceiverWindow()
    
    
    # 连接信号槽
    timer_window.time_updated.connect(receiver_window.update_time_display)
    timer_window.time_updated.connect(receiver_window2.update_time_display)
    timer_window.time_updated.connect(receiver_window3.update_time_display)

    # 显示窗口
    timer_window.show()
    receiver_window.show()
    receiver_window2.show()
    receiver_window3.show()

    
    res = app.exec()

    sys.exit(res)