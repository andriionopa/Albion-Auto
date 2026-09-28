import cv2
import time


class ZoneTransitionService:
    def __init__(self, exit_template_path):
        self.template = cv2.imread(exit_template_path, cv2.IMREAD_GRAYSCALE) if exit_template_path else None
        if self.template is not None:
            self.th, self.tw = self.template.shape[:2]
        else:
            self.th = self.tw = 0

        self.threshold = 0.60
        self.state = "IDLE"
        self._state_time = time.time()

        self.debug = False
        self.log = None

    def debug_log(self, msg):
        if self.debug and self.log:
            self.log(f"[Zone] {msg}")

    def find_exit_on_screen(self, frame):
        if self.template is None or self.template.size == 0:
            return None
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(gray, self.template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val < self.threshold:
            return None
        cx = max_loc[0] + self.tw // 2
        cy = max_loc[1] + self.th // 2
        self.debug_log(f"Exit found at ({cx},{cy}) conf={max_val:.2f}")
        return cx, cy

    def is_loading_screen(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return float(gray.mean()) < 12.0

    def set_state(self, state):
        self.state = state
        self._state_time = time.time()
        self.debug_log(f"State → {state}")

    def elapsed(self):
        return time.time() - self._state_time

    def set_template(self, path):
        self.template = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if self.template is not None:
            self.th, self.tw = self.template.shape[:2]
