from dataclasses import dataclass, field


@dataclass
class BotConfig:
    # Anchor Service
    anchor_threshold: float = 0.43
    anchor_color_ratio: float = 0.13
    stuck_limit: int = 30
    anchor_hex_color_orange: str = "#d3ce00"
    anchor_hex_color_blue: str = "#0a64b1"
    anchor_example_path: str = "MountHealthBar/MountHealthBar.png"
    anchor_debug: bool = False

    # Fishing Service
    missing_frame_limits: int = 2
    tolerance_for_bober: int = 45
    tolerance_for_bober_ratio: float = 0.0006
    bobber_example_path: str = "bobberExamples/bobberExample2.png"
    bober_color_hex: str = "#FF3F2D"
    fishing_debug: bool = False

    # Gathering Service
    tolerance_for_gathering: int = 35
    tolerance_for_gathering_ratio: float = 0.30
    gathering_debug: bool = False

    # Player Service
    tolerance_for_player: int = 35
    tolerance_for_player_ratio: float = 0.10
    player_color_hex: str = "#d0460d"
    player_debug: bool = False

    # Telegram Service
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Radar & Escape
    radar_binary_path: str = "./OpenRadar.exe"
    exit_template_path: str = "exitExamples/exit.png"
    vk_invis: int = 0x32
    player_danger_radius: int = 60
    chat_response_chance: float = 0.65
    radar_enabled: bool = True

    debug: bool = False
