import datetime
import random
import cv2
import win32api
import time
import win32con
import requests

from app import config
from app.utils import check_color_ratio
from app.WindowCapture import WindowCaptureService


class WeightStatusService:
    def __init__(self, anchor_service):
        self.TELEGRAM_TOKEN = config.TELEGRAM_TOKEN
        self.CHAT_ID = config.CHAT_ID
        self.last_update_id = None
        self.VK_Z = 0x5A
        self.VK_I = 0x49

        self.ALERT_ANNOUNCEMENT = None
        self.ON_MOUNT = False

        self.capture_service = WindowCaptureService()
        self.anchor_service = anchor_service

        self.now = time.time()
        self.checking_handle_commands = self.now

    def send_telegram_screenshot(self, frame, filename="screenshot.png", caption="Скріншот"):
        if not self.TELEGRAM_TOKEN:
            return
        cv2.imwrite(filename, frame)
        url = f"https://api.telegram.org/bot{self.TELEGRAM_TOKEN}/sendPhoto"
        try:
            with open(filename, "rb") as f:
                requests.post(url, files={"photo": f}, data={"chat_id": self.CHAT_ID, "caption": caption}, timeout=5)
        except Exception as e:
            print(f"[Telegram] Помилка скріншоту: {e}")

    def send_telegram_message(self, text):
        if not self.TELEGRAM_TOKEN:
            return
        url = f"https://api.telegram.org/bot{self.TELEGRAM_TOKEN}/sendMessage"
        try:
            requests.get(url, params={"chat_id": self.CHAT_ID, "text": text}, timeout=5)
        except Exception as e:
            print(f"[Telegram] Помилка повідомлення: {e}")

    def handle_updates(self):
        if not self.TELEGRAM_TOKEN:
            return
        url = f"https://api.telegram.org/bot{self.TELEGRAM_TOKEN}/getUpdates"
        params = {}
        if self.last_update_id is not None:
            params["offset"] = self.last_update_id + 1
        try:
            resp = requests.get(url, params=params, timeout=5).json()
        except Exception:
            return
        for update in resp.get("result", []):
            self.last_update_id = update["update_id"]
            if "message" not in update:
                continue
            text = update["message"].get("text", "")
            if text == "/check_screen":
                self.press_key_i()
                time.sleep(random.uniform(1, 1.5))
                frame = self.capture_service.capture_window(config.WINDOW_TITLE)
                self.press_key_i()
                self.send_telegram_screenshot(frame=frame, caption="Скріншот за запитом")
            elif text == "/press z":
                self.press_key_z()
                time.sleep(random.uniform(1, 1.5))
                frame = self.capture_service.capture_window(config.WINDOW_TITLE)
                self.send_telegram_screenshot(frame=frame, caption="Натиснув Z")
            elif text == "/enable_walk" and self.anchor_service is not None:
                self.anchor_service.stop_moving = False
                self.send_telegram_message("Знову рухаюсь!")

    def crop_top_right_square(self, frame, size=28, offset_x=348, offset_y=54):
        h, w, _ = frame.shape
        x1 = max(0, w - size - offset_x)
        y1 = min(max(0, offset_y), h - size)
        return frame[y1:y1 + size, x1:x1 + size].copy()

    def press_key_z(self):
        win32api.keybd_event(self.VK_Z, 0, 0, 0)
        time.sleep(random.uniform(0.05, 0.15))
        win32api.keybd_event(self.VK_Z, 0, win32con.KEYEVENTF_KEYUP, 0)

    def press_key_i(self):
        win32api.keybd_event(self.VK_I, 0, 0, 0)
        time.sleep(random.uniform(0.05, 0.15))
        win32api.keybd_event(self.VK_I, 0, win32con.KEYEVENTF_KEYUP, 0)

    def process_weight_status(self, frame):
        self.now = time.time()
        weight_icon = self.crop_top_right_square(frame)
        found_weight, ratio_weight = check_color_ratio(weight_icon, "#9B3B3F", tolerance=35, min_ratio=0.01)

        if self.now - self.checking_handle_commands > 10:
            self.handle_updates()
            self.checking_handle_commands = self.now

        return weight_icon, found_weight, ratio_weight

    def process(self):
        if not self.ON_MOUNT:
            self.press_key_z()
            time.sleep(5 * random.uniform(0.8, 1.10))
            self.ON_MOUNT = True

        frame = self.capture_service.capture_window(config.WINDOW_TITLE)
        if frame is None:
            return
        weight_icon = self.crop_top_right_square(frame)
        found_weight, _ = check_color_ratio(weight_icon, "#9B3B3F", tolerance=35, min_ratio=0.01)
        if not found_weight:
            return

        if self.ALERT_ANNOUNCEMENT is None:
            self.send_telegram_screenshot(frame=weight_icon, caption="Максимальна вага — треба розвантажитись!")
            self.ALERT_ANNOUNCEMENT = datetime.datetime.now()
            return

        if (datetime.datetime.now() - self.ALERT_ANNOUNCEMENT).seconds >= 600:
            self.send_telegram_screenshot(frame=weight_icon, caption="Максимальна вага — треба розвантажитись!")
            self.ALERT_ANNOUNCEMENT = datetime.datetime.now()
