from PySide6.QtCore import QThread, Signal

from app import config as app_config
from app.AppEnter import AppEnterService


class BotWorker(QThread):
    log = Signal(str)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.bot = None

    def run(self):
        self.bot = AppEnterService(
            self.config.bobber_example_path,
            self.config.anchor_example_path,
            exit_template_path=self.config.exit_template_path,
        )

        # Anchor
        self.bot.DEBUG = self.config.debug
        self.bot.anchor_service.threshold = self.config.anchor_threshold
        self.bot.anchor_service.stuck_limit = self.config.stuck_limit
        self.bot.anchor_service.hex_color_blue = self.config.anchor_hex_color_blue
        self.bot.anchor_service.hex_color_orange = self.config.anchor_hex_color_orange
        self.bot.anchor_service.debug = self.config.anchor_debug
        self.bot.anchor_service.log = self.log.emit

        # Fishing
        self.bot.fishing_service.tolerance_for_bobber = self.config.tolerance_for_bober
        self.bot.fishing_service.tolerance_ration_min_value = self.config.tolerance_for_bober_ratio
        self.bot.fishing_service.MISSING_FRAMES_LIMIT = self.config.missing_frame_limits
        self.bot.fishing_service.debug = self.config.fishing_debug
        self.bot.fishing_service.log = self.log.emit

        # Gathering
        self.bot.gathering_service.tolerance = self.config.tolerance_for_gathering
        self.bot.gathering_service.min_ratio = self.config.tolerance_for_gathering_ratio
        self.bot.gathering_service.debug = self.config.gathering_debug
        self.bot.gathering_service.log = self.log.emit

        # Player
        self.bot.player_status.tolerance = self.config.tolerance_for_player
        self.bot.player_status.min_ratio = self.config.tolerance_for_player_ratio
        self.bot.player_status.hex_color_orange = self.config.player_color_hex
        self.bot.player_status.debug = self.config.player_debug
        self.bot.player_status.log = self.log.emit

        # Telegram
        self.bot.weight_status.TELEGRAM_TOKEN = self.config.telegram_bot_token
        self.bot.weight_status.CHAT_ID = self.config.telegram_chat_id
        self.bot.anchor_service.weight_status_service.TELEGRAM_TOKEN = self.config.telegram_bot_token
        self.bot.anchor_service.weight_status_service.CHAT_ID = self.config.telegram_chat_id

        # Radar & Escape
        app_config.RADAR_BINARY_PATH = self.config.radar_binary_path
        app_config.VK_INVIS = self.config.vk_invis
        app_config.PLAYER_DANGER_RADIUS = self.config.player_danger_radius
        app_config.CHAT_RESPONSE_CHANCE = self.config.chat_response_chance

        if not self.config.radar_enabled:
            self.bot.radar._connected = False

        self.log.emit("Запущено!")
        try:
            self.bot.run()
        except Exception as e:
            self.log.emit(f"Помилка: {e}")

    def stop(self):
        self.terminate()
