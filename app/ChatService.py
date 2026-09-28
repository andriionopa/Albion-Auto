import random
import time
import win32api
import win32con
import win32gui

from app import config


class ChatService:
    def __init__(self):
        self._last_check = time.time()
        self._pending = []
        self._typing_until = 0.0

    def feed_messages(self, messages):
        for msg in messages:
            if random.random() < config.CHAT_RESPONSE_CHANCE:
                delay = random.uniform(*config.CHAT_RESPONSE_DELAY)
                self._pending.append({
                    "respond_at": time.time() + delay,
                    "text": random.choice(config.CHAT_RESPONSES),
                    "from": msg.get("sender", ""),
                })

    def tick(self):
        if time.time() < self._typing_until:
            return

        now = time.time()
        due = [p for p in self._pending if p["respond_at"] <= now]
        if not due:
            return

        self._pending = [p for p in self._pending if p["respond_at"] > now]
        entry = due[-1]
        self._type_in_chat(entry["text"])

    def _type_in_chat(self, text):
        hwnd = win32gui.FindWindow(None, config.WINDOW_TITLE)
        if not hwnd:
            return

        self._typing_until = time.time() + len(text) * 0.12 + 2.0

        self._send_key(win32con.VK_RETURN)
        time.sleep(random.uniform(0.25, 0.45))

        for char in text:
            vk = win32api.VkKeyScan(char)
            if vk == -1:
                continue
            vk_code = vk & 0xFF
            shift = (vk >> 8) & 0xFF

            if shift & 1:
                win32api.keybd_event(win32con.VK_SHIFT, 0, 0, 0)

            win32api.keybd_event(vk_code, 0, 0, 0)
            time.sleep(random.uniform(0.04, 0.11))
            win32api.keybd_event(vk_code, 0, win32con.KEYEVENTF_KEYUP, 0)

            if shift & 1:
                win32api.keybd_event(win32con.VK_SHIFT, 0, win32con.KEYEVENTF_KEYUP, 0)

            time.sleep(random.uniform(0.03, 0.08))

        time.sleep(random.uniform(0.15, 0.35))
        self._send_key(win32con.VK_RETURN)

    def _send_key(self, vk):
        win32api.keybd_event(vk, 0, 0, 0)
        time.sleep(random.uniform(0.05, 0.12))
        win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
