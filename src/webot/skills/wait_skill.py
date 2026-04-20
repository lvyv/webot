# -*- coding: utf-8 -*-
# skills/wait_skill.py

import time
from ..utils import get_logger

logger = get_logger(__name__)

def wait_for_user_focus(seconds=3, message="请切换到微信聊天窗口"):
    logger.info(f"{message}，{seconds} 秒后继续执行...")
    time.sleep(seconds)