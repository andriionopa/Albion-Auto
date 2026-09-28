import cv2
import numpy as np
import random
import time
import win32api
import win32con

from app.utils import check_color_ratio
from app.WeightStatus import WeightStatusService


class AnchorForMoovmentService:
    def __init__(self, anchor_path):
        self.template = cv2.imread(anchor_path, cv2.IMREAD_GRAYSCALE)
        self.th, self.tw = self.template.shape[:2]
        self.threshold = 0.43
        self.stuck_limit = 300
        self.hex_color_orange = "#d3ce00"
        self.hex_color_blue = "#0a64b1"

        self.VK_W = 0x57
        self.VK_A = 0x41
        self.VK_S = 0x53
        self.VK_D = 0x44
        self.VK_Z = 0x5A

        self.stuck_counter = 0
        self.screenshot_sent = False
        self.stop_moving = False
        self.weight_status_service = WeightStatusService(anchor_service=None)

        self.debug = False
        self.log = None

    def debug_log(self, message):
        if self.debug and self.log is not None:
            self.log(f"[Anchor Log] {message}")

    def press_random_key(self):
        key = random.choice([self.VK_W, self.VK_D, self.VK_A, self.VK_S])
        win32api.keybd_event(key, 0, 0, 0)
        time.sleep(random.uniform(0.05, 0.15))
        win32api.keybd_event(key, 0, win32con.KEYEVENTF_KEYUP, 0)

    def press_z_key(self):
        win32api.keybd_event(self.VK_Z, 0, 0, 0)
        time.sleep(random.uniform(0.05, 0.15))
        win32api.keybd_event(self.VK_Z, 0, win32con.KEYEVENTF_KEYUP, 0)

    def restart_anchor(self):
        self.stuck_counter = 0
        self.stop_moving = False
        self.screenshot_sent = False
        self.press_z_key()
        time.sleep(10)
        self.press_z_key()
        for _ in range(2):
            self.press_random_key()

    def process_found_anchor(self, frame):
        if self.stop_moving:
            self.restart_anchor()
            return None

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(gray, self.template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val < self.threshold:
            return None

        x, y = max_loc
        y -= 7
        roi = frame[y:y + self.th + 7, x:x + self.tw]

        color_ok, ratio = check_color_ratio(roi, self.hex_color_orange, tolerance=35, min_ratio=0.10)
        self.debug_log(f"Orange {color_ok} | ratio {ratio:.4f}")

        if not color_ok:
            self._handle_stuck(frame)
            return None

        color_ok_blue, ratio_blue = check_color_ratio(roi, self.hex_color_blue, tolerance=35, min_ratio=0.10)
        self.debug_log(f"Blue {color_ok_blue} | ratio {ratio_blue:.4f}")

        if color_ok_blue:
            self._handle_stuck(frame)
            return None

        self.stuck_counter = 0
        self.screenshot_sent = False

        cx = max_loc[0] + self.tw // 2
        cy = max_loc[1] + self.th // 2

        cv2.rectangle(frame, max_loc, (max_loc[0] + self.tw, max_loc[1] + self.th), (0, 255, 0), 2)
        cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
        return cx, cy

    def _handle_stuck(self, frame):
        self.press_random_key()
        self.stuck_counter += 1
        if self.stuck_counter > self.stuck_limit and not self.screenshot_sent:
            self.weight_status_service.send_telegram_screenshot(
                frame=frame, caption="Застряв — не можу знайти куди рухатись!"
            )
            self.screenshot_sent = True
            self.stop_moving = True
