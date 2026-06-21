# -*- coding: utf-8 -*-
# utils.py

import pyautogui
import logging
from importlib.resources import files, as_file
from .config import FAILSAFE_ENABLED

pyautogui.FAILSAFE = FAILSAFE_ENABLED

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logging.getLogger().setLevel(logging.INFO)


def get_logger(name):
    return logging.getLogger(name)


def get_image_path(filename):
    resource = files('webot.images') / filename
    with as_file(resource) as path:
        return str(path)