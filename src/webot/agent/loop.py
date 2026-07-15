import multiprocessing
import threading
from collections import deque
from queue import Empty

from ..utils import AGENT_MAX_TOOL_ITERATIONS
from ..utils import get_logger
from ..skills.reddot_skill import get_unread_chats
from ..skills.auto_reply_skill import (
    load_rules,
    should_auto_reply,
    select_reply,
    process_single_chat,
    find_file_helper_y,
    send_confirm_request,
)

logger = get_logger(__name__)


PENDING_CONFIRM_PREFIX = "pending_confirm:"


def _extract_confirm_info(task_messages: str) -> dict | None:
    """从文件传输助手的 OCR 文本中解析确认回复。"""
    lines = task_messages.strip().split("\n")
    chat_name = None
    action = None
    modified_text = None
    for line in lines:
        line = line.strip()
        if line.startswith("联系人："):
            chat_name = line[4:].strip()
        elif line == "@同意":
            action = "agree"
        elif line == "@拒绝":
            action = "reject"
        elif line.startswith("@修改:"):
            action = "modify"
            modified_text = line[4:].strip()
    if chat_name and action:
        return {
            "chat_name": chat_name,
            "action": action,
            "modified_text": modified_text,
        }
    return None


class ReplyWorker(multiprocessing.Process):
    """纯计算 Worker，从 task_queue 取任务，处理后将操作指令发往 reply_queue。"""

    def __init__(self, task_queue, reply_queue, reply_mode="template",
                 llm_model="deepseek-chat"):
        super().__init__()
        self._task_queue = task_queue
        self._reply_queue = reply_queue
        self._reply_mode = reply_mode
        self._llm_model = llm_model
        self.daemon = True
        self._pending: dict[str, dict] = {}
        self._last_messages: dict[str, str] = {}

    def run(self):
        self._init_worker()
        logger.info("ReplyWorker 已就绪")
        while True:
            try:
                task = self._task_queue.get()
                if task is None:
                    break
            except (EOFError, OSError):
                break

            try:
                task = self._dedup_task(task)
                if task is None:
                    continue
                self._process(task)
            except Exception as e:
                logger.error(f"Worker 处理异常: {e}")

    def _dedup_task(self, task):
        """比较本次 OCR 文本与上次处理的内容，提取新消息。"""
        chat_name = task["chat_name"]
        messages = task.get("messages", "")
        if not messages:
            return None

        last = self._last_messages.get(chat_name, "")
        if not last:
            self._last_messages[chat_name] = messages
            return task

        # 查找旧文本在新文本中的位置（旧文本可能是新文本的子串）
        pos = messages.find(last)
        if pos >= 0:
            new_part = (messages[:pos] + messages[pos + len(last):]).strip()
        else:
            new_part = messages

        if not new_part:
            logger.info(f"[{chat_name}] 无新消息，跳过")
            return None

        self._last_messages[chat_name] = messages
        task["new_messages"] = new_part
        return task

    def _init_worker(self):
        from .memory import Memory, JsonLinesBackend
        from .session import Session
        from .llm_client import LLMClient
        from .skill_manager import SkillManager
        from ..skills import register_all_skills

        self._memory = Memory(backend=JsonLinesBackend())
        self._session = Session()
        self._llm_client = LLMClient(model=self._llm_model)
        self._skill_mgr = SkillManager()
        register_all_skills(self._skill_mgr)
        self._llm = self._llm_client if self._llm_client.available else None
        self._rules = load_rules()

    def _process(self, task):
        chat_name = task["chat_name"]
        preview = task.get("preview", "")
        messages = task.get("messages", "")

        pending_key = f"{PENDING_CONFIRM_PREFIX}{chat_name}"
        if pending_key in self._pending:
            self._handle_confirm_reply(task)
            return

        if chat_name == "文件传输助手":
            confirm = _extract_confirm_info(messages or preview)
            if confirm:
                self._handle_confirm_response(confirm)
            return

        # 提取本次新增的消息
        new_messages = task.get("new_messages", messages)

        logger.info(f"Worker 处理 [{chat_name}]（新消息长度: {len(new_messages)}）")

        if self._reply_mode in ("llm", "llm_with_fallback"):
            ok = self._process_llm(chat_name, messages, preview, new_messages)
            if not ok and self._reply_mode == "llm_with_fallback":
                self._process_template(chat_name, task)
        else:
            self._process_template(chat_name, task)

    def _process_template(self, chat_name, task):
        reply_text = select_reply(self._rules)
        if not reply_text:
            logger.info(f"[{chat_name}] 无匹配模板回复，跳过")
            return

        if self._is_needs_confirm(chat_name):
            self._pending[f"{PENDING_CONFIRM_PREFIX}{chat_name}"] = {
                "reply_text": reply_text,
                "click_y": task["position"]["y"],
            }
            self._reply_queue.put({
                "action": "ask_confirm",
                "chat_name": chat_name,
                "reply_text": reply_text,
            })
        else:
            self._reply_queue.put({
                "action": "reply",
                "chat_name": chat_name,
                "click_y": task["position"]["y"],
                "reply_text": reply_text,
            })

    def _process_llm(self, chat_name, messages, preview, new_messages=None):
        if not self._llm:
            return False

        system_prompt = "你是一个微信自动助手。根据收到的消息，选择合适的工具或直接回复。"
        llm_messages = [{"role": "system", "content": system_prompt}]

        history = self._memory.get_history(chat_name, limit=10)
        for h in history:
            llm_messages.append({"role": h["role"], "content": h.get("content", "")})

        ctx = self._session.get_context(chat_name)
        for c in ctx:
            llm_messages.append(c)

        user_content = f"来自 [{chat_name}] 的消息:\n{new_messages or messages or preview}"
        if new_messages and new_messages != messages:
            user_content = (
                f"【聊天完整内容】\n{messages}\n\n"
                f"【本次新增消息】\n{new_messages}"
            )
        llm_messages.append({"role": "user", "content": user_content})

        tools = self._skill_mgr.get_tools_spec() if self._skill_mgr else []

        iteration = 0
        try:
            resp = self._llm.chat(llm_messages, tools=tools if tools else None)
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return False

        while resp.get("type") == "tool_calls" and iteration < AGENT_MAX_TOOL_ITERATIONS:
            iteration += 1
            for tc in resp.get("tool_calls", []):
                result = self._skill_mgr.execute(tc["name"], tc["arguments"])
                llm_messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })
            llm_messages = self._session.intervene(chat_name, llm_messages)
            try:
                resp = self._llm.chat(llm_messages, tools=tools if tools else None)
            except Exception as e:
                logger.error(f"LLM 第 {iteration} 轮调用失败: {e}")
                return False

        reply = resp.get("content", "")
        if not reply:
            return False

        self._memory.save_message(chat_name, "user", messages or preview)
        self._memory.save_message(chat_name, "assistant", reply)
        self._session.add_message(chat_name, "user", messages or preview)
        self._session.add_message(chat_name, "assistant", reply)

        self._reply_queue.put({
            "action": "llm_reply",
            "chat_name": chat_name,
            "reply_text": reply,
        })
        return True

    def _handle_confirm_reply(self, task):
        pending_key = f"{PENDING_CONFIRM_PREFIX}{task['chat_name']}"
        info = self._pending.pop(pending_key, None)
        if info:
            self._reply_queue.put({
                "action": "reply",
                "chat_name": task["chat_name"],
                "click_y": info["click_y"],
                "reply_text": info["reply_text"],
            })

    def _handle_confirm_response(self, confirm):
        chat_name = confirm["chat_name"]
        pending_key = f"{PENDING_CONFIRM_PREFIX}{chat_name}"
        info = self._pending.pop(pending_key, None)
        if info is None:
            logger.warning(f"收到 [{chat_name}] 的确认回复，但无待确认记录")
            return

        if confirm["action"] == "agree":
            self._reply_queue.put({
                "action": "reply",
                "chat_name": chat_name,
                "click_y": info["click_y"],
                "reply_text": info["reply_text"],
            })
        elif confirm["action"] == "reject":
            logger.info(f"主人拒绝了 [{chat_name}] 的回复")
        elif confirm["action"] == "modify" and confirm["modified_text"]:
            self._reply_queue.put({
                "action": "reply",
                "chat_name": chat_name,
                "click_y": info["click_y"],
                "reply_text": confirm["modified_text"],
            })

    @staticmethod
    def _is_needs_confirm(chat_name):
        return False


class MainLoop:
    """UI 进程内的调度器：负责执行 reply 指令 + 截图识别 + 任务入队。"""

    def __init__(self):
        self.rules = load_rules()
        self._seen_chats = {}
        self._processed_count = 0
        self._first_tick = True
        self.reply_mode = "template"
        self.auto_reply_enabled = True
        self.current_processing = None
        self._pending_chats: deque = deque()

        self._task_queue = multiprocessing.Queue()
        self._reply_queue = multiprocessing.Queue()
        self._worker = ReplyWorker(
            task_queue=self._task_queue,
            reply_queue=self._reply_queue,
            reply_mode=self.reply_mode,
        )

    def start_worker(self):
        if self._worker.is_alive():
            return
        self._worker = ReplyWorker(
            task_queue=self._task_queue,
            reply_queue=self._reply_queue,
            reply_mode=self.reply_mode,
        )
        self._worker.start()
        self._result_thread = threading.Thread(target=self._collect_results, daemon=True)
        self._result_thread.start()
        logger.info("Worker 已启动")

    def stop_worker(self):
        if self._worker.is_alive():
            self._task_queue.put(None)
            self._worker.join(timeout=3)

    def reset(self):
        self._seen_chats.clear()
        self._processed_count = 0
        self._first_tick = True
        self.current_processing = None
        self._pending_chats.clear()

    def reload_rules(self):
        self.rules = load_rules()

    def _collect_results(self):
        """后台线程：持续读取 reply_queue 的结果，更新 processed_count。"""
        while True:
            try:
                instr = self._reply_queue.get()
                if instr.get("action") in ("reply", "llm_reply"):
                    self._processed_count += 1
            except Exception:
                break

    def tick(self):
        if not self.auto_reply_enabled:
            return [], self._processed_count, self.current_processing

        if not self._worker.is_alive():
            logger.warning("Worker 未运行，启动 Worker")
            self.start_worker()

        self._consume_reply_queue()

        try:
            unreads = get_unread_chats()
        except Exception as e:
            logger.error(f"检测未读异常: {e}")
            return [], self._processed_count, self.current_processing

        # 首次 tick：记录所有未读，不加入队列，不处理
        if self._first_tick:
            self._first_tick = False
            for m in unreads:
                self._seen_chats[m["chat_name"]] = m.get("preview", "")
            if unreads:
                logger.info(f"首次发现 {len(unreads)} 个未读（已记录，本次不处理）")
            return unreads, self._processed_count, self.current_processing

        # 检测新未读，加入待处理队列（FIFO）
        for m in unreads:
            name = m["chat_name"]
            preview = m.get("preview", "")

            if name in self._seen_chats:
                if self._seen_chats[name] == preview:
                    continue
                logger.info(f"[{name}] 有新消息: {preview[:60]}")

            self._seen_chats[name] = preview

            if not should_auto_reply(name, self.rules):
                continue

            self._pending_chats.append(m)
            logger.info(f"[{name}] 加入待处理队列（队列长度 {len(self._pending_chats)}）")

        # 每 tick 从队列头部处理一个联系人（FIFO）
        if self._pending_chats:
            m = self._pending_chats.popleft()
            name = m["chat_name"]
            self.current_processing = name
            logger.info(f"[{name}] 开始处理（剩余队列 {len(self._pending_chats)}）")

            messages = process_single_chat(m)
            
            if messages:
                logger.info(f"[{name}] 聊天内容:\n{messages[:200]}")
                task = {**m, "messages": messages}
                self._task_queue.put(task)
            else:
                logger.warning(f"[{name}] 未读取到聊天消息")

            self.current_processing = None

        return unreads, self._processed_count, self.current_processing

    def _consume_reply_queue(self):
        """消费 reply_queue 中的所有待执行指令（非阻塞）。"""
        while True:
            try:
                instr = self._reply_queue.get_nowait()
            except Empty:
                break

            action = instr.get("action", "")
            logger.info(f"执行 reply 指令: {action} -> {instr.get('chat_name', '')}")

            try:
                if action in ("reply", "llm_reply"):
                    self._execute_reply(instr)
                elif action == "ask_confirm":
                    self._execute_ask_confirm(instr)
            except Exception as e:
                logger.error(f"执行指令失败 {action}: {e}")

    def _execute_reply(self, instr):
        """执行回复操作：点击联系人 → 发送消息。"""
        click_y = instr.get("click_y")
        if click_y is not None:
            from ..skills.auto_reply_skill import click_chat_by_position
            click_chat_by_position({"y": click_y})
        chat_name = instr.get("chat_name", "")
        reply_text = instr.get("reply_text", "")
        if reply_text:
            from ..skills.auto_reply_skill import send_reply
            send_reply(reply_text)
            logger.info(f"已回复 [{chat_name}]: {reply_text[:60]}")
        self.current_processing = None

    def _execute_ask_confirm(self, instr):
        """执行确认请求：找到文件传输助手 → 发送确认消息。"""
        chat_name = instr.get("chat_name", "")
        reply_text = instr.get("reply_text", "")
        helper_y = find_file_helper_y()
        if helper_y is not None:
            send_confirm_request(helper_y, chat_name, reply_text)
            logger.info(f"已向主人发送确认请求: [{chat_name}] -> {reply_text[:60]}")
            self.current_processing = f"待确认: {chat_name}"
        else:
            logger.warning("未找到文件传输助手，无法发送确认请求")
