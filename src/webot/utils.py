# -*- coding: utf-8 -*-
# utils.py

import pyautogui
import logging
from .config import FAILSAFE_ENABLED

pyautogui.FAILSAFE = FAILSAFE_ENABLED

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

def get_logger(name):
    return logging.getLogger(name)