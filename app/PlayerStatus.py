import random
import win32api
import time
import win32con
from datetime import datetime

from app.utils import check_color_ratio


class PlayerStatusService:
    def __init__(self):
        self.VK_1 = 0x31
        self.VK_3 = 0x33
        self.cooldown = datetime.now()
        self.hex_color_orange = "#d0460d"
        self.tolerance = 35
        self.min_ratio = 0.1
        self.debug = False
        self.log = None

    def debug_log(self, message):
        if self.debug and self.log is not None:
            self.log(f"[Player Log] {message}")

    def crop_top_left_square(self, frame, size=60, offset_x=24, offset_y=45):
        h, w, _ = frame.shape
        x1 = min(max(0, offset_x), w - size)
        y1 = min(max(0, offset_y), h - size)
        return frame[y1:y1 + size, x1:x1 + size].copy()

    def press_key_1(self):
        win32api.keybd_event(self.VK_1, 0, 0, 0)
        time.sleep(random.uniform(0.05, 0.15))
        win32api.keybd_event(self.VK_1, 0, win32con.KEYEVENTF_KEYUP, 0)

    def process_player_status(self, frame):
        character_icon = self.crop_top_left_square(frame)
        found, ratio = check_color_ratio(
            character_icon, self.hex_color_orange,
            tolerance=self.tolerance, min_ratio=self.min_ratio
        )
        self.debug_log(f"Player {found} | ratio {ratio:.4f}")
        return character_icon, found, ratio

    def process(self):
        self.debug_log("Атакують!")
        self.press_key_1()
        time.sleep(4 * random.uniform(0.8, 1.10))
