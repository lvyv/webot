# -*- coding: utf-8 -*-
# utils.py

import pyautogui
import logging
from .config import FAILSAFE_ENABLED

pyautogui.FAILSAFE = FAILSAFE_ENABLED

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def get_logger(name):
    return logging.getLogger(name)