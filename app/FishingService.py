import random
import cv2
import time
import win32api
import win32con
import win32gui
import numpy as np

from app.utils import check_color_ratio
from app import config


class FishingService:
    def __init__(self, bober_example_path):
        self.bobberExample = cv2.imread(bober_example_path, cv2.IMREAD_GRAYSCALE)
        self.bobberExampleInWatter = cv2.imread("bobberExamples/bobberExampleInWatter2.png", cv2.IMREAD_GRAYSCALE)
        self.h, self.w = self.bobberExample.shape[:2]
        self.h_in, self.w_in = self.bobberExampleInWatter.shape[:2]

        self.tolerance_for_bobber = 45
        self.tolerance_ratio_min = 0.0006
        self.bober_color_hex = "#FF3F2D"

        self.last_bobber_y = None
        self.missing_frames = 0
        self.MISSING_FRAMES_LIMIT = 2

        self.mouse_down = False
        self.previous_misses = []
        self.state_enter_time = time.time()
        self.last_seen_time = time.time()
        self.NO_OBJECT_TIMEOUT = 2.0
        self.state = "STARTING"

        self.debug = False
        self.log = None

    def debug_log(self, message):
        if self.debug and self.log is not None:
            self.log(f"[Fishing Log] {message}")

    def set_state(self, new_state):
        self.state = new_state
        self.state_enter_time = time.time()
        if new_state == "MINI GAME":
            self.last_seen_time = time.time()
            self.mouse_down = False
        self.debug_log(f"STATE → {new_state}")

    def mouse_press(self):
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        self.mouse_down = True

    def mouse_release(self):
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        self.mouse_down = False

    def crop_center(self, frame, crop_w=130, crop_h=50):
        h, w, _ = frame.shape
        cx = w // 2
        cy = h // 2 + 18
        x1 = max(cx - crop_w // 2, 0)
        y1 = max(cy - crop_h // 2, 0)
        x2 = min(cx + crop_w // 2, w)
        y2 = min(cy + crop_h // 2, h)
        return frame[y1:y2, x1:x2]

    def get_game_window_rect(self, window_title):
        hwnd = win32gui.FindWindow(None, window_title)
        if not hwnd:
            return None
        return win32gui.GetWindowRect(hwnd)

    def map_mouse_to_frame(self, frame):
        rect = self.get_game_window_rect(config.WINDOW_TITLE)
        if not rect:
            return None, None
        left, top, right, bottom = rect
        mx, my = win32api.GetCursorPos()
        rel_x = mx - left
        rel_y = my - top
        if rel_x < 0 or rel_y < 0 or rel_x > right - left or rel_y > bottom - top:
            return None, None
        fh, fw, _ = frame.shape
        return int(rel_x * fw / (right - left)), int(rel_y * fh / (bottom - top))

    def crop_mouse_area(self, frame, crop_w=100, crop_h=100):
        fx, fy = self.map_mouse_to_frame(frame)
        if fx is None:
            return None
        x1 = max(fx - crop_w // 2, 0)
        y1 = max(fy - crop_h // 2, 0)
        x2 = min(fx + crop_w // 2, frame.shape[1])
        y2 = min(fy + crop_h // 2, frame.shape[0])
        return frame[y1:y2, x1:x2]

    def find_bobber_in_roi(self, roi):
        found, ratio = check_color_ratio(
            roi, self.bober_color_hex,
            tolerance=self.tolerance_for_bobber,
            min_ratio=self.tolerance_ratio_min
        )
        self.debug_log(f"Bobber found={found} ratio={ratio:.6f}")
        if found:
            return True, ratio
        return None, ratio

    def start_state(self):
        if time.time() - self.state_enter_time < 3:
            return
        self.mouse_press()
        time.sleep(random.uniform(0.38, 0.75))
        self.mouse_release()
        time.sleep(2)
        self.set_state("HOOK")

    def reset_state(self):
        if self.mouse_down:
            self.mouse_release()
        if time.time() - self.state_enter_time < 0.5:
            return
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        self.set_state("STARTING")

    def hook_state(self, frame):
        if time.time() - self.state_enter_time < 1:
            return frame

        roi = self.crop_mouse_area(frame, crop_w=350, crop_h=440)
        if roi is None:
            return frame

        pos, score = self.find_bobber_in_roi(roi)

        if pos is None:
            self.missing_frames += 1
            if self.missing_frames >= self.MISSING_FRAMES_LIMIT:
                if len(self.previous_misses) >= 2:
                    self.mouse_press()
                    time.sleep(0.05)
                    self.mouse_release()
                    self.set_state("MINI GAME")
                else:
                    self.debug_log("No bobber — RESTART")
                    self.set_state("RESTART")
                self.last_bobber_y = None
                self.missing_frames = 0
                self.previous_misses = []
            return roi

        self.missing_frames = 0
        if len(self.previous_misses) < 3:
            self.previous_misses.append(1)
        return roi

    def find_bober(self, frame):
        cropped = self.crop_center(frame, 130, 50)
        if cropped is None or cropped.size == 0:
            return frame

        frame = cv2.resize(cropped, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        res = cv2.matchTemplate(gray_frame, self.bobberExample, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if max_val < 0.7:
            if time.time() - self.last_seen_time > self.NO_OBJECT_TIMEOUT:
                self.set_state("RESTART")
            return frame

        self.last_seen_time = time.time()
        x, y = max_loc
        cv2.rectangle(frame, (x, y), (x + self.w, y + self.h), (0, 255, 255), 2)

        if x <= 130:
            if not self.mouse_down:
                self.mouse_press()
        elif x >= 160:
            if self.mouse_down:
                self.mouse_release()

        return frame

    def controller(self, frame):
        if self.state == "STARTING":
            self.start_state()
        elif self.state == "HOOK":
            self.hook_state(frame)
        elif self.state == "MINI GAME":
            self.find_bober(frame)
        elif self.state == "RESTART":
            self.reset_state()
