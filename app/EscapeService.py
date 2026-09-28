import math
import random
import time
import win32api
import win32con

from app import config


class EscapeService:
    def __init__(self, zone_transition, mouse_service, anchor_service, capture_service, radar, weight_status):
        self.zone_transition = zone_transition
        self.mouse_service = mouse_service
        self.anchor_service = anchor_service
        self.capture_service = capture_service
        self.radar = radar
        self.weight_status = weight_status

        self.state = "IDLE"
        self._state_time = time.time()
        self._last_move_time = 0.0
        self._invis_pressed_at = 0.0

        self.debug = False
        self.log = None

    def debug_log(self, msg):
        if self.debug and self.log:
            self.log(f"[Escape] {msg}")

    def is_active(self):
        return self.state != "IDLE"

    def _set_state(self, state):
        self.state = state
        self._state_time = time.time()
        self.debug_log(f"→ {state}")

    def _elapsed(self):
        return time.time() - self._state_time

    def _press_key(self, vk):
        win32api.keybd_event(vk, 0, 0, 0)
        time.sleep(random.uniform(0.06, 0.14))
        win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)

    def trigger(self, players_nearby):
        names = [p["name"] for p in players_nearby]
        msg = f"Гравці поруч: {', '.join(names)} — маунтуюсь і тікаю!"
        print(f"[Escape] {msg}")
        self.weight_status.send_telegram_message(msg)
        self._set_state("MOUNTING")

    def tick(self, frame):
        if self.state == "MOUNTING":
            return self._tick_mounting(frame)
        if self.state == "INVISIBLE":
            return self._tick_invisible(frame)
        if self.state == "FINDING_EXIT":
            return self._tick_finding_exit(frame)
        if self.state == "LOADING":
            return self._tick_loading(frame)
        return False

    def _tick_mounting(self, frame):
        if self._elapsed() < 0.3:
            self._press_key(config.VK_MOUNT)
            return True
        if self._elapsed() > 2.5:
            self._press_key(config.VK_INVIS)
            self._invis_pressed_at = time.time()
            self._set_state("INVISIBLE")
        return True

    def _tick_invisible(self, frame):
        if self.zone_transition.is_loading_screen(frame):
            self._set_state("LOADING")
            return True

        elapsed_invis = time.time() - self._invis_pressed_at
        if elapsed_invis > config.ESCAPE_INVIS_DURATION:
            self._press_key(config.VK_INVIS)
            self._invis_pressed_at = time.time()

        exit_pos = self.zone_transition.find_exit_on_screen(frame)
        if exit_pos:
            self.mouse_service.aim_and_click_win32(exit_pos[0], exit_pos[1], frame, False)
            self._set_state("FINDING_EXIT")
            return True

        if time.time() - self._last_move_time > random.uniform(2.0, 3.5):
            self._move_toward_exit(frame)
            self._last_move_time = time.time()

        return True

    def _tick_finding_exit(self, frame):
        if self.zone_transition.is_loading_screen(frame):
            self._set_state("LOADING")
            return True

        if self._elapsed() > config.ESCAPE_MAX_SEARCH_TIME:
            self.weight_status.send_telegram_message("Не знайшов виход — зупинився!")
            self._set_state("IDLE")
            return False

        exit_pos = self.zone_transition.find_exit_on_screen(frame)
        if exit_pos and self._elapsed() > 1.5:
            self.mouse_service.aim_and_click_win32(exit_pos[0], exit_pos[1], frame, False)
            self._set_state("FINDING_EXIT")
            return True

        if time.time() - self._last_move_time > random.uniform(3.0, 5.0):
            self._move_toward_exit(frame)
            self._last_move_time = time.time()

        return True

    def _tick_loading(self, frame):
        if not self.zone_transition.is_loading_screen(frame):
            self.weight_status.send_telegram_message("Перейшов в іншу локацію — продовжую фарм!")
            self._set_state("IDLE")
            return False
        return True

    def _move_toward_exit(self, frame):
        fh, fw, _ = frame.shape

        exits = self.radar.get_exits() if self.radar.is_connected() else []
        if exits:
            nearest = min(
                exits,
                key=lambda e: math.hypot(e["x"] - self.radar.my_x, e["y"] - self.radar.my_y)
            )
            cx, cy = self._game_dir_to_screen(
                self.radar.my_x, self.radar.my_y,
                nearest["x"], nearest["y"],
                fw, fh
            )
        else:
            anchor_coords = self.anchor_service.process_found_anchor(frame)
            if anchor_coords:
                cx, cy = anchor_coords
            else:
                cx = fw // 2 + random.randint(-fw // 4, fw // 4)
                cy = fh // 2 + random.randint(-fh // 4, fh // 4)

        self.mouse_service.aim_and_click_win32(cx, cy, frame, False)

    def _game_dir_to_screen(self, px, py, tx, ty, fw, fh):
        dx = tx - px
        dy = -(ty - py)
        dist = math.hypot(dx, dy)
        if dist < 1:
            return fw // 2, fh // 2

        nx = dx / dist
        ny = dy / dist
        reach = min(fw, fh) * 0.35
        cx = int(fw // 2 + nx * reach)
        cy = int(fh // 2 + ny * reach)
        cx = max(60, min(fw - 60, cx))
        cy = max(60, min(fh - 60, cy))
        return cx, cy
