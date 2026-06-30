import time

from ..config import AGENT_POLL_INTERVAL, AGENT_MAX_TOOL_ITERATIONS
from ..utils import get_logger
from ..skills.reddot_skill import get_unread_chats
from ..skills.auto_reply_skill import load_rules, should_auto_reply, select_reply, process_chat

logger = get_logger(__name__)


class ReplyMode:
    TEMPLATE = "template"
    LLM = "llm"
    LLM_FALLBACK = "llm_with_fallback"


class AgentLoop:
    def __init__(self, skill_manager=None, memory=None, session=None, llm_client=None):
        self.skill_manager = skill_manager
        self.memory = memory
        self.session = session
        self.llm_client = llm_client
        self.rules = load_rules()

        self._seen_chats = {}
        self._processed_count = 0
        self._first_tick = True
        self.reply_mode = ReplyMode.TEMPLATE
        self.auto_reply_enabled = True

    def reset(self):
        self._seen_chats.clear()
        self._processed_count = 0
        self._first_tick = True

    def reload_rules(self):
        self.rules = load_rules()

    def tick(self):
        if not self.auto_reply_enabled:
            return [], 0

        try:
            unreads = get_unread_chats()
        except Exception as e:
            logger.error(f"检测未读异常: {e}")
            return [], self._processed_count

        if self._first_tick:
            self._first_tick = False
            for m in unreads:
                self._seen_chats[m["chat_name"]] = m.get("preview", "")
            if unreads:
                logger.info(f"首次发现 {len(unreads)} 个未读（已记录，本次不处理）")
            return unreads, self._processed_count

        for m in unreads:
            name = m["chat_name"]
            preview = m.get("preview", "")

            if name in self._seen_chats:
                old = self._seen_chats[name]
                if old == preview:
                    continue
                logger.info(f"[{name}] 有新消息: {preview[:60]}")

            self._seen_chats[name] = preview

            if not should_auto_reply(name, self.rules):
                logger.info(f"[{name}] 不在自动回复列表，保留红点不处理")
                continue

            logger.info(f"[{name}] 属于自动回复范围，开始处理")
            ok = self._handle_one(name, m["item_index"], preview)
            if ok:
                self._processed_count += 1

        return unreads, self._processed_count

    def _handle_one(self, chat_name, item_index, preview):
        logger.info(f"处理 [{chat_name}] 的未读消息，预览: {preview[:60]}")
        if self.reply_mode == ReplyMode.TEMPLATE:
            logger.info(f"[{chat_name}] 模板匹配聊天模式启动.")
            return self._handle_template(chat_name, item_index)
        elif self.reply_mode == ReplyMode.LLM:
            logger.info(f"[{chat_name}] LLM 聊天模式启动.")
            return self._handle_llm(chat_name, item_index, preview)
        elif self.reply_mode == ReplyMode.LLM_FALLBACK:
            logger.info(f"[{chat_name}] LLM_FALLBACK 模式启动.")    
            ok = self._handle_llm(chat_name, item_index, preview)
            if not ok:
                logger.info(f"[{chat_name}] LLM 回复失败，降级到模板匹配")
                return self._handle_template(chat_name, item_index)
            return ok
        return False

    def _handle_template(self, chat_name, item_index):
        try:
            ok = process_chat(chat_name, item_index, self.rules)
        except Exception as e:
            logger.error(f"处理 [{chat_name}] 时出错: {e}")
            return False
        if ok and self.memory:
            self.memory.save_message(chat_name, "assistant", select_reply(self.rules) or "(已回复)")
        if ok and self.session:
            self.session.add_message(chat_name, "assistant", select_reply(self.rules) or "(已回复)")
        return ok

    def _handle_llm(self, chat_name, item_index, preview):
        if not self.llm_client:
            logger.warning("LLM 客户端未初始化，跳过 LLM 回复")
            return False

        from ..skills.auto_reply_skill import click_chat_by_index, read_chat_area, send_reply
        from ..skills.window_skill import activate_window
        from ..config import WECHAT_WINDOW_TITLE, WECHAT_WINDOW_CLSNAME

        import time
        if not activate_window(WECHAT_WINDOW_TITLE, WECHAT_WINDOW_CLSNAME):
            return False
        time.sleep(0.5)
        if not click_chat_by_index(item_index):
            return False

        messages = read_chat_area()
        if not messages:
            logger.warning("未读取到聊天消息")
            return False

        system_prompt = "你是一个微信自动助手。根据收到的消息，选择合适的工具或直接回复。"
        llm_messages = [{"role": "system", "content": system_prompt}]

        if self.memory:
            history = self.memory.get_history(chat_name, limit=10)
            for h in history:
                llm_messages.append({"role": h["role"], "content": h.get("content", "")})

        if self.session:
            ctx = self.session.get_context(chat_name)
            for c in ctx:
                llm_messages.append(c)

        llm_messages.append({"role": "user", "content": f"来自 [{chat_name}] 的消息:\n{messages}"})

        tools = []
        if self.skill_manager:
            tools = self.skill_manager.get_tools_spec()

        iteration = 0
        max_iterations = AGENT_MAX_TOOL_ITERATIONS

        try:
            resp = self.llm_client.chat(llm_messages, tools=tools if tools else None)
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return False

        while resp["type"] == "tool_calls" and iteration < max_iterations:
            iteration += 1
            for tc in resp["tool_calls"]:
                result = self.skill_manager.execute(tc["name"], tc["arguments"])
                llm_messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })
            if self.session:
                llm_messages = self.session.intervene(chat_name, llm_messages)
            try:
                resp = self.llm_client.chat(llm_messages, tools=tools if tools else None)
            except Exception as e:
                logger.error(f"LLM 第 {iteration} 轮调用失败: {e}")
                return False

        if iteration >= max_iterations:
            logger.warning(f"LLM tool 调用达到上限 {max_iterations}，取当前结果")

        reply = resp.get("content", "")

        if not reply:
            return False

        if not send_reply(reply):
            return False

        if self.memory:
            self.memory.save_message(chat_name, "user", messages)
            self.memory.save_message(chat_name, "assistant", reply)

        if self.session:
            self.session.add_message(chat_name, "user", messages)
            self.session.add_message(chat_name, "assistant", reply)

        return True
