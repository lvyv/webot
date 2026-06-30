#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
from PyQt6.QtWidgets import QApplication
from webot.ui import WebotWindow


def main():
    app = QApplication(sys.argv)
    window = WebotWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
