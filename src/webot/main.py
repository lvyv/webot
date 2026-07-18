#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
from PyQt6.QtWidgets import QApplication
from webot.ui import WebotWindow
from webot.utils.config import FAILSAFE_ENABLED
from dotenv import find_dotenv, load_dotenv
import pyautogui



def main():
    env_path = find_dotenv()
    if env_path:
        load_dotenv(env_path)
    pyautogui.FAILSAFE = FAILSAFE_ENABLED

    app = QApplication(sys.argv)
    window = WebotWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
