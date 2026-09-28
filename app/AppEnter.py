import random
import time
import win32api
import win32con
import cv2

from app import config
from app.WindowCapture import WindowCaptureService
from app.PlayerStatus import PlayerStatusService
from app.WeightStatus import WeightStatusService
from app.YoloModel import YoloModelService
from app.MouseService import MouseService
from app.WaterCluster import WaterClusterService
from app.AnchorForMoovment import AnchorForMoovmentService
from app.GatheringService import GatheringService
from app.FishingService import FishingService
from app.ZoneTransitionService import ZoneTransitionService
from app.RadarClient import RadarClient
from app.EscapeService import EscapeService
from app.ChatService import ChatService


class AppEnterService:
    def __init__(self, bober_example_path, anchor_example_path, exit_template_path=None):
        self.DEBUG = False
        self.stage = "Start"
        self.stage_interapter = None
        self.trees_not_found = 0

        self.capture_service = WindowCaptureService()
        self.player_status = PlayerStatusService()
        self.yolo_model = YoloModelService()
        self.mouse_service = MouseService()
        self.water_cluster = WaterClusterService()
        self.anchor_service = AnchorForMoovmentService(anchor_example_path)
        self.weight_status = WeightStatusService(anchor_service=self.anchor_service)
        self.gathering_service = GatheringService()
        self.fishing_service = FishingService(bober_example_path)
        self.zone_transition = ZoneTransitionService(exit_template_path)
        self.chat_service = ChatService()

        self.radar = RadarClient()
        self.radar.start()

        self.escape_service = EscapeService(
            zone_transition=self.zone_transition,
            mouse_service=self.mouse_service,
            anchor_service=self.anchor_service,
            capture_service=self.capture_service,
            radar=self.radar,
            weight_status=self.weight_status,
        )

        self.now = time.time()
        self.last_player_check = self.now
        self.last_yolo_check = self.now
        self.last_chat_check = self.now

        self.start_gathering_time = self.now
        self.start_fishing_time = self.now
        self.eating_pie_time = self.now

        self.first_pie = False
        self.player_icon = None
        self.weight_icon = None
        self.yolo_model_frame = None
        self.found_gathering_history = []

    def _press_key(self, vk):
        win32api.keybd_event(vk, 0, 0, 0)
        time.sleep(random.uniform(0.1, 0.2))
        win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)

    def run(self):
        while True:
            frame = self.capture_service.capture_window(config.WINDOW_TITLE)
            if frame is None:
                time.sleep(0.05)
                continue

            self.now = time.time()

            if self.zone_transition.is_loading_screen(frame):
                time.sleep(1.0)
                continue

            if not self.first_pie:
                self._press_key(config.VK_PIE)
                self.first_pie = True
                time.sleep(random.uniform(3, 4))
                self.eating_pie_time = self.now

            if self.escape_service.is_active():
                self.escape_service.tick(frame)
                self._maybe_show_debug()
                time.sleep(0.01)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
                continue

            self.chat_service.tick()

            if self.now - self.last_chat_check > 2.0:
                msgs = self.radar.pop_new_chat_messages(since_time=self.last_chat_check)
                if msgs:
                    self.chat_service.feed_messages(msgs)
                self.last_chat_check = self.now

            if self.now - self.last_player_check > 0.2:
                self.player_icon, founded_attack, _ = self.player_status.process_player_status(frame)
                self.last_player_check = self.now
                if founded_attack:
                    self.player_status.process()
                    self.stage_interapter = "Player Under Attack"
                elif self.stage_interapter == "Player Under Attack":
                    self.stage = "Start"
                    self.stage_interapter = None

            if self.stage_interapter != "Player Under Attack":
                self.weight_icon, founded_overweight, _ = self.weight_status.process_weight_status(frame)
                if founded_overweight:
                    self.weight_status.process()
                    self.stage_interapter = "Player Over Weight"
                else:
                    self.weight_status.ON_MOUNT = False
                    if self.stage_interapter == "Player Over Weight":
                        self.stage = "Start"
                        self.stage_interapter = None

            if self.stage_interapter is not None:
                time.sleep(0.05)
                continue

            if self.radar.is_connected():
                nearby = self.radar.get_players_nearby()
                if nearby:
                    self.escape_service.trigger(nearby)
                    time.sleep(0.01)
                    continue

            if self.stage == "Start":
                self._run_start(frame)
            elif self.stage == "Scan Tree":
                self._run_scan_tree(frame)
            elif self.stage == "Gathering":
                self._run_gathering(frame)
            elif self.stage == "Scan Water":
                self._run_scan_water(frame)
            elif self.stage == "Fishing":
                self._run_fishing(frame)

            self._maybe_show_debug()
            time.sleep(0.01)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cv2.destroyAllWindows()

    def _run_start(self, frame):
        anchor_coords = self.anchor_service.process_found_anchor(frame)
        if anchor_coords:
            self.mouse_service.aim_and_click_win32(anchor_coords[0], anchor_coords[1], frame, False)
            time.sleep(random.uniform(4, 5))
            self.stage = "Scan Tree"

    def _run_scan_tree(self, frame):
        if self.now - self.last_yolo_check < 1.0:
            return
        self.yolo_model_frame, tree_positions = self.yolo_model.process_yolo_model(frame)
        self.last_yolo_check = self.now

        trees = [p for p in tree_positions if p[2] == "treee_v4"]
        if trees:
            tx, ty, _ = trees[0]
            self.mouse_service.aim_and_click_win32(tx, ty, frame, True)
            time.sleep(random.uniform(3, 4))
            self.start_gathering_time = self.now
            self.stage = "Gathering"
            self.trees_not_found = 0
            return

        self.trees_not_found += 1
        if self.trees_not_found > random.uniform(6, 10):
            self.trees_not_found = 0
            if self.radar.is_connected() and not self.radar.has_resources_nearby():
                self.escape_service._set_state("FINDING_EXIT")
                self.weight_status.send_telegram_message("Ресурсів немає — шукаю вихід в іншу локацію")
            else:
                self.stage = "Scan Water"

    def _run_gathering(self, frame):
        if self.now - self.start_gathering_time > random.uniform(*config.GATHERING_TIMEOUT):
            self.stage = "Start"
            return
        found, _ = self.gathering_service.find_gathering_indicator(frame)
        if not found:
            self.found_gathering_history.append(False)
            if len(self.found_gathering_history) >= 3:
                self.found_gathering_history = []
                self.stage = "Start"
        else:
            self.found_gathering_history = []

    def _run_scan_water(self, frame):
        _, water_pos = self.water_cluster.process_water_cluster(frame)
        if water_pos:
            self.mouse_service.aim_and_click_win32(water_pos[0], water_pos[1], frame, False)
            time.sleep(random.uniform(3, 4))
            self.start_fishing_time = self.now
            self.stage = "Fishing"
            frame2 = self.capture_service.capture_window(config.WINDOW_TITLE)
            if frame2 is not None:
                _, water_pos2 = self.water_cluster.process_water_cluster(frame2)
                if water_pos2:
                    self.mouse_service.aim_and_click_win32(water_pos2[0], water_pos2[1], frame2, False)

    def _run_fishing(self, frame):
        if self.now - self.eating_pie_time > config.PIE_DURATION_SECONDS:
            self._press_key(config.VK_PIE)
            time.sleep(random.uniform(3, 4))
            self.eating_pie_time = self.now

        if self.now - self.start_fishing_time > random.uniform(*config.FISHING_TIMEOUT):
            self.fishing_service.reset_state()
            self.stage = "Start"
            return

        if self.fishing_service.state == "RESTART":
            _, water_pos = self.water_cluster.process_water_cluster(frame)
            if water_pos:
                self.mouse_service.aim_and_click_win32(water_pos[0], water_pos[1], frame, False)

        self.fishing_service.controller(frame)

    def _maybe_show_debug(self):
        if not self.DEBUG:
            return
        if self.player_icon is not None:
            cv2.imshow("Char Icon", self.player_icon)
        if self.weight_icon is not None:
            cv2.imshow("Weight Icon", self.weight_icon)
        if self.yolo_model_frame is not None:
            cv2.imshow("(Live)", self.yolo_model_frame)
