# -*- coding: utf-8 -*-
# config.py

APP_NAME = "webot"
WECHAT_WINDOW_TITLE = "微信"
MOMENTS_WINDOW_TITLE = "朋友圈"
WECHAT_WINDOW_CLSNAME = "Qt51514QWindowIcon"
DEFAULT_WINDOW_WIDTH = 1000
DEFAULT_WINDOW_HEIGHT = 800

INPUT_SEARCH_CONTACT = "search_contact.png"
INPUT_MESSAGE_IN = "message_in.png"
BTN_CONTACTS_IMAGE = "contacts.png"
IMG_SHORTCUTS = "shortcuts.png"
IMG_IMAGE = "image.png"
IMG_MOMENTS = "moments.png"         # 左边栏朋友圈
IMG_POST = "post.png"               # 朋友圈评论 ..
IMG_CHAT_HISTORY = "history.png"    # 聊天历史信息
IMG_CLOSE_BUTTON = "close.png"      # 关闭按钮
IMG_MSG_INPUT_RIGHT_UP_CORNER = "input_right_up_corner.png"
IMG_INPUT_SEARCH_CONTACT = "search_contact.png"


CONFIDENCE_LEVEL = 0.8
OCR_CONFIDENCE_THRESHOLD = 0.8

RETRY_TIMES = 3
RETRY_DELAY = 0.5
POST_CLICK_DELAY = 0.5
PASTE_DELAY = 0.3
SCROLL_DELAY = 0.1

FAILSAFE_ENABLED = True

# chat_ocr_skill
CHAT_REGION_THRESHOLD = 30
CHAT_MIN_CONTOUR_AREA = 500
CHAT_OVERLAP_MAX_SEARCH = 800
CHAT_BLEND_WIDTH = 25


# agent / reddot_skill
AGENT_POLL_INTERVAL = 5.0
AGENT_MAX_TOOL_ITERATIONS = 10

CHAT_ITEM_HEIGHT = 25               # 为了确保联系人项目之间距离能够区分开，25以内是项内文字块垂直间隔，大于25就是新的一项
SHORTCUTS_CENTER_TO_LIST_RIGHT = 25 # 为了找到联系人列表面板的右边界
CHAT_LIST_LEFT_OFFSET = 60          # 聊天列表左侧偏移，为了正确进入联系人列表面板/为了通过聊天历史图标进入聊天历史窗口
CHAT_LIST_TOP_OFFSET = 80           # 窗口顶端下偏移，为了正确进入联系人列表面板/为了通过聊天历史图标进入聊天历史窗口
CHAT_LIST_TAB_WIDTH = 0             # 聊天列表左侧的标签页宽度
CHAT_LIST_WIDTH_RATIO = 0.30

RED_DOT_HUE_LOW1 = 0        # 红色的HSV表示的H1下限
RED_DOT_HUE_HIGH1 = 10      # 红色的HSV表示的H1上限
RED_DOT_HUE_LOW2 = 170      # 红色的HSV表示的H2下限
RED_DOT_HUE_HIGH2 = 180     # 红色的HSV表示的H2上限
RED_DOT_SAT_MIN = 80        # 红色的HSV表示的S
RED_DOT_VAL_MIN = 80        # 红色的HSV表示的V
RED_DOT_AREA_MIN = 35   # 小红点面积下限
RED_DOT_AREA_MAX = 45   # 小红点面积上限
RED_DOT_AREA_MIN2 = 110 # 大红点面积下限
RED_DOT_AREA_MAX2 = 175 # 大红点面积上限
RED_DOT_OFFSET_X = 20  # 小红点中心相对于聊天项右侧的水平偏移
RED_DOT_OFFSET_Y = 10  # 小红点中心相对于聊天项顶部的垂直偏移

PANEL_CHAT_HISTORY_TOP_OFFSET = 80   # 聊天历史图标下偏移到面板可滚动区域

# panel_rect_skill
TITLE_BAR_HEIGHT = 32                # Windows 标准标题栏高度
LEFT_TOOLBAR_WIDTH = 58              # 微信左侧边工具栏宽度
CHAT_HISTORY_TOP_OFFSET = 120        # 聊天历史区域上边界距窗口顶部偏移
CHAT_INPUT_HEIGHT = 150              # 消息输入框区域高度
RIGHT_PANEL_RIGHT_MARGIN = 10        # 右侧面板右边距
