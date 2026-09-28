import cv2
from app.utils import check_color_ratio


class GatheringService:
    def __init__(self):
        self.tolerance = 35
        self.min_ratio = 0.30
        self.debug = False
        self.log = None

    def debug_log(self, message):
        if self.debug and self.log is not None:
            self.log(f"[Gathering Log] {message}")

    def crop_center(self, frame, crop_w=250, crop_h=40):
        h, w, _ = frame.shape
        cx = w // 2 - 91
        cy = h // 2 + 160
        x1 = max(cx - crop_w // 2, 0)
        y1 = max(cy - crop_h // 2, 0)
        x2 = min(cx + crop_w // 2, w)
        y2 = min(cy + crop_h // 2, h)
        return frame[y1:y2, x1:x2]

    def find_gathering_indicator(self, frame):
        cropped = self.crop_center(frame, 7, 55)
        found, ratio = check_color_ratio(cropped, "#31556D", tolerance=self.tolerance, min_ratio=self.min_ratio)
        self.debug_log(f"Gathering {found} | ratio {ratio:.4f}")
        return found, ratio
