import sys
import time
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton


class TimerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QTimer Test")
        self.setGeometry(300, 300, 300, 150)  # x, y, width, height
        
        # 创建UI组件
        self.label = QLabel("Timer not started...")
        self.button = QPushButton("Start Timer")
        
        # 创建布局
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.button)
        self.setLayout(layout)
        
        # 创建定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_label)
        
        # 连接按钮信号
        self.button.clicked.connect(self.toggle_timer)
    
    def update_label(self):
        """定时器触发时更新标签"""
        if self.timer.isActive():
            current_time = time.strftime('%H:%M:%S')
            self.label.setText(f"Timer triggered at {current_time}")
    
    def toggle_timer(self):
        """切换定时器启动/停止"""
        if self.timer.isActive():
            self.timer.stop()
            self.button.setText("Start Timer")
            self.label.setText("Timer stopped")
        else:
            self.timer.start(2000)  # 每2秒触发一次
            self.button.setText("Stop Timer")
            self.label.setText("Timer started...")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = TimerWindow()
    window.show()
    
    sys.exit(app.exec())