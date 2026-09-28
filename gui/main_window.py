import subprocess
import sys

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QDoubleSpinBox, QSpinBox, QTextEdit, QCheckBox,
    QGroupBox, QTabWidget, QLineEdit, QColorDialog, QFileDialog
)
from PySide6.QtGui import QColor, QPixmap
from gui.config import BotConfig
from gui.worker import BotWorker


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Albion Control Panel")
        self.resize(460, 580)

        self.config = BotConfig()
        self.worker = None
        self._radar_proc = None

        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.addTab(self._build_anchor_tab(), "Anchor")
        tabs.addTab(self._build_fishing_tab(), "Fishing")
        tabs.addTab(self._build_gathering_tab(), "Gathering")
        tabs.addTab(self._build_player_tab(), "Player")
        tabs.addTab(self._build_telegram_tab(), "Telegram")
        tabs.addTab(self._build_radar_tab(), "Radar & Escape")

        self.debug_checkbox = QCheckBox("Debug mode")

        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("▶ Start")
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)

        self.logs = QTextEdit()
        self.logs.setReadOnly(True)

        layout.addWidget(tabs)
        layout.addWidget(self.debug_checkbox)
        layout.addLayout(btn_layout)
        layout.addWidget(QLabel("Logs"))
        layout.addWidget(self.logs)

        self.start_btn.clicked.connect(self.start_bot)
        self.stop_btn.clicked.connect(self.stop_bot)

    def _build_anchor_tab(self):
        box = QGroupBox()
        layout = QVBoxLayout()

        self.anchor_threshold = QDoubleSpinBox()
        self.anchor_threshold.setDecimals(2)
        self.anchor_threshold.setRange(0, 1)
        self.anchor_threshold.setSingleStep(0.01)
        self.anchor_threshold.setValue(self.config.anchor_threshold)

        self.anchor_color_ratio = QDoubleSpinBox()
        self.anchor_color_ratio.setDecimals(2)
        self.anchor_color_ratio.setRange(0, 1)
        self.anchor_color_ratio.setSingleStep(0.01)
        self.anchor_color_ratio.setValue(self.config.anchor_color_ratio)

        self.stuck_limit = QSpinBox()
        self.stuck_limit.setRange(10, 500)
        self.stuck_limit.setValue(self.config.stuck_limit)

        self.anchor_debug = QCheckBox()
        self.anchor_debug.setChecked(self.config.anchor_debug)

        self.anchor_color_btn_one = QPushButton("Anchor Color (orange)")
        self.current_anchor_one_color = QColor(self.config.anchor_hex_color_orange)
        self._apply_color_btn(self.anchor_color_btn_one, self.current_anchor_one_color)
        self.anchor_color_btn_one.clicked.connect(
            lambda: self._pick_color(self.anchor_color_btn_one, "current_anchor_one_color")
        )

        self.anchor_color_btn_two = QPushButton("Anchor Color (blue — skip)")
        self.current_anchor_two_color = QColor(self.config.anchor_hex_color_blue)
        self._apply_color_btn(self.anchor_color_btn_two, self.current_anchor_two_color)
        self.anchor_color_btn_two.clicked.connect(
            lambda: self._pick_color(self.anchor_color_btn_two, "current_anchor_two_color")
        )

        self.anchor_path_edit = QLineEdit(self.config.anchor_example_path)
        self.anchor_preview = QLabel()
        self.anchor_preview.setFixedSize(320, 30)
        self.anchor_preview.setScaledContents(True)
        self.anchor_preview.setStyleSheet("border: 1px solid gray;")
        self.anchor_preview.setPixmap(QPixmap(self.anchor_path_edit.text()))

        select_btn = QPushButton("Select Anchor Template")
        select_btn.clicked.connect(lambda: self._pick_file(self.anchor_path_edit, self.anchor_preview))

        for w, lbl in [
            (self.anchor_threshold, "Template threshold"),
            (self.anchor_color_ratio, "Anchor color ratio"),
            (self.stuck_limit, "Stuck limit"),
            (self.anchor_color_btn_one, ""),
            (self.anchor_color_btn_two, ""),
            (self.anchor_path_edit, "Anchor Template Path"),
            (select_btn, ""),
            (self.anchor_preview, ""),
            (self.anchor_debug, "Debug mode"),
        ]:
            if lbl:
                layout.addWidget(QLabel(lbl))
            layout.addWidget(w)

        box.setLayout(layout)
        return box

    def _build_fishing_tab(self):
        box = QGroupBox()
        layout = QVBoxLayout()

        self.missing_frame_limits = QSpinBox()
        self.missing_frame_limits.setRange(1, 30)
        self.missing_frame_limits.setValue(self.config.missing_frame_limits)

        self.tolerance_for_bober = QSpinBox()
        self.tolerance_for_bober.setRange(1, 100)
        self.tolerance_for_bober.setValue(self.config.tolerance_for_bober)

        self.tolerance_for_bober_ratio = QDoubleSpinBox()
        self.tolerance_for_bober_ratio.setDecimals(4)
        self.tolerance_for_bober_ratio.setRange(0.0001, 1)
        self.tolerance_for_bober_ratio.setSingleStep(0.0001)
        self.tolerance_for_bober_ratio.setValue(self.config.tolerance_for_bober_ratio)

        self.bober_color_btn = QPushButton("Bobber Color")
        self.current_bober_color = QColor(self.config.bober_color_hex)
        self._apply_color_btn(self.bober_color_btn, self.current_bober_color)
        self.bober_color_btn.clicked.connect(
            lambda: self._pick_color(self.bober_color_btn, "current_bober_color")
        )

        self.bobber_path_edit = QLineEdit(self.config.bobber_example_path)
        self.bobber_preview = QLabel()
        self.bobber_preview.setFixedSize(40, 40)
        self.bobber_preview.setScaledContents(True)
        self.bobber_preview.setStyleSheet("border: 1px solid gray;")
        self.bobber_preview.setPixmap(QPixmap(self.bobber_path_edit.text()))

        select_btn = QPushButton("Select Bobber Template")
        select_btn.clicked.connect(lambda: self._pick_file(self.bobber_path_edit, self.bobber_preview))

        self.fishing_debug = QCheckBox()
        self.fishing_debug.setChecked(self.config.fishing_debug)

        for w, lbl in [
            (self.missing_frame_limits, "Missing frame hook limit"),
            (self.tolerance_for_bober, "Bobber tolerance"),
            (self.tolerance_for_bober_ratio, "Bobber ratio"),
            (self.bober_color_btn, ""),
            (self.bobber_path_edit, "Bobber template"),
            (select_btn, ""),
            (self.bobber_preview, ""),
            (self.fishing_debug, "Debug mode"),
        ]:
            if lbl:
                layout.addWidget(QLabel(lbl))
            layout.addWidget(w)

        box.setLayout(layout)
        return box

    def _build_gathering_tab(self):
        box = QGroupBox()
        layout = QVBoxLayout()

        self.tolerance_for_gathering = QSpinBox()
        self.tolerance_for_gathering.setRange(1, 100)
        self.tolerance_for_gathering.setValue(self.config.tolerance_for_gathering)

        self.tolerance_for_gathering_ratio = QDoubleSpinBox()
        self.tolerance_for_gathering_ratio.setDecimals(2)
        self.tolerance_for_gathering_ratio.setRange(0, 1)
        self.tolerance_for_gathering_ratio.setSingleStep(0.01)
        self.tolerance_for_gathering_ratio.setValue(self.config.tolerance_for_gathering_ratio)

        self.gathering_debug = QCheckBox()
        self.gathering_debug.setChecked(self.config.gathering_debug)

        for w, lbl in [
            (self.tolerance_for_gathering, "Gathering tolerance"),
            (self.tolerance_for_gathering_ratio, "Gathering ratio"),
            (self.gathering_debug, "Debug mode"),
        ]:
            if lbl:
                layout.addWidget(QLabel(lbl))
            layout.addWidget(w)

        box.setLayout(layout)
        return box

    def _build_player_tab(self):
        box = QGroupBox()
        layout = QVBoxLayout()

        self.tolerance_for_player = QSpinBox()
        self.tolerance_for_player.setRange(1, 100)
        self.tolerance_for_player.setValue(self.config.tolerance_for_player)

        self.tolerance_for_player_ratio = QDoubleSpinBox()
        self.tolerance_for_player_ratio.setDecimals(2)
        self.tolerance_for_player_ratio.setRange(0, 1)
        self.tolerance_for_player_ratio.setSingleStep(0.01)
        self.tolerance_for_player_ratio.setValue(self.config.tolerance_for_player_ratio)

        self.player_color_btn = QPushButton("Player HP Color")
        self.current_player_color = QColor(self.config.player_color_hex)
        self._apply_color_btn(self.player_color_btn, self.current_player_color)
        self.player_color_btn.clicked.connect(
            lambda: self._pick_color(self.player_color_btn, "current_player_color")
        )

        self.player_debug = QCheckBox()
        self.player_debug.setChecked(self.config.player_debug)

        for w, lbl in [
            (self.tolerance_for_player, "Player tolerance"),
            (self.tolerance_for_player_ratio, "Player ratio"),
            (self.player_color_btn, ""),
            (self.player_debug, "Debug mode"),
        ]:
            if lbl:
                layout.addWidget(QLabel(lbl))
            layout.addWidget(w)

        box.setLayout(layout)
        return box

    def _build_telegram_tab(self):
        box = QGroupBox()
        layout = QVBoxLayout()

        self.telegram_token = QLineEdit(self.config.telegram_bot_token)
        self.telegram_token.setEchoMode(QLineEdit.Password)

        self.telegram_chat_id = QLineEdit(self.config.telegram_chat_id)
        self.telegram_chat_id.setEchoMode(QLineEdit.Password)

        show_btn = QPushButton("👁 Show / Hide")

        def toggle():
            mode = QLineEdit.Normal if self.telegram_token.echoMode() == QLineEdit.Password else QLineEdit.Password
            self.telegram_token.setEchoMode(mode)
            self.telegram_chat_id.setEchoMode(mode)

        show_btn.clicked.connect(toggle)

        layout.addWidget(QLabel("Bot Token"))
        layout.addWidget(self.telegram_token)
        layout.addWidget(QLabel("Chat ID"))
        layout.addWidget(self.telegram_chat_id)
        layout.addWidget(show_btn)
        box.setLayout(layout)
        return box

    def _build_radar_tab(self):
        box = QGroupBox()
        layout = QVBoxLayout()

        self.radar_enabled = QCheckBox("Enable radar (OpenRadar)")
        self.radar_enabled.setChecked(self.config.radar_enabled)

        self.radar_path_edit = QLineEdit(self.config.radar_binary_path)
        select_radar = QPushButton("Select OpenRadar.exe")
        select_radar.clicked.connect(lambda: self._pick_file(self.radar_path_edit, None, "*.exe"))

        self.exit_path_edit = QLineEdit(self.config.exit_template_path)
        self.exit_preview = QLabel()
        self.exit_preview.setFixedSize(80, 80)
        self.exit_preview.setScaledContents(True)
        self.exit_preview.setStyleSheet("border: 1px solid gray;")
        self.exit_preview.setPixmap(QPixmap(self.exit_path_edit.text()))
        select_exit = QPushButton("Select Exit Template (screenshot)")
        select_exit.clicked.connect(lambda: self._pick_file(self.exit_path_edit, self.exit_preview))

        self.vk_invis = QSpinBox()
        self.vk_invis.setRange(0, 255)
        self.vk_invis.setValue(self.config.vk_invis)
        self.vk_invis.setDisplayIntegerBase(16)
        self.vk_invis.setPrefix("0x")

        self.danger_radius = QSpinBox()
        self.danger_radius.setRange(10, 300)
        self.danger_radius.setValue(self.config.player_danger_radius)

        self.chat_chance = QDoubleSpinBox()
        self.chat_chance.setDecimals(2)
        self.chat_chance.setRange(0, 1)
        self.chat_chance.setSingleStep(0.05)
        self.chat_chance.setValue(self.config.chat_response_chance)

        layout.addWidget(self.radar_enabled)
        layout.addWidget(QLabel("OpenRadar.exe path"))
        layout.addWidget(self.radar_path_edit)
        layout.addWidget(select_radar)
        layout.addWidget(QLabel("Exit portal template (screenshot of exit)"))
        layout.addWidget(self.exit_path_edit)
        layout.addWidget(select_exit)
        layout.addWidget(self.exit_preview)
        layout.addWidget(QLabel("Invis skill key (hex VK code)"))
        layout.addWidget(self.vk_invis)
        layout.addWidget(QLabel("Player danger radius (game units)"))
        layout.addWidget(self.danger_radius)
        layout.addWidget(QLabel("Chat response chance (0–1)"))
        layout.addWidget(self.chat_chance)

        box.setLayout(layout)
        return box

    def _apply_color_btn(self, btn, color):
        btn.setFixedHeight(30)
        btn.setStyleSheet(f"background-color: {color.name()};")

    def _pick_color(self, btn, attr_name):
        current = getattr(self, attr_name)
        color = QColorDialog.getColor(current, self)
        if color.isValid():
            setattr(self, attr_name, color)
            self._apply_color_btn(btn, color)

    def _pick_file(self, line_edit, preview_label, filter_str="Images (*.png *.jpg *.jpeg)"):
        path, _ = QFileDialog.getOpenFileName(self, "Select file", "", filter_str)
        if path:
            line_edit.setText(path)
            if preview_label is not None:
                preview_label.setPixmap(QPixmap(path))

    def start_bot(self):
        self.config.anchor_threshold = self.anchor_threshold.value()
        self.config.anchor_color_ratio = self.anchor_color_ratio.value()
        self.config.stuck_limit = self.stuck_limit.value()
        self.config.anchor_hex_color_orange = self.current_anchor_one_color.name()
        self.config.anchor_hex_color_blue = self.current_anchor_two_color.name()
        self.config.anchor_example_path = self.anchor_path_edit.text()
        self.config.anchor_debug = self.anchor_debug.isChecked()

        self.config.missing_frame_limits = self.missing_frame_limits.value()
        self.config.tolerance_for_bober = self.tolerance_for_bober.value()
        self.config.tolerance_for_bober_ratio = self.tolerance_for_bober_ratio.value()
        self.config.bober_color_hex = self.current_bober_color.name()
        self.config.bobber_example_path = self.bobber_path_edit.text()
        self.config.fishing_debug = self.fishing_debug.isChecked()

        self.config.tolerance_for_gathering = self.tolerance_for_gathering.value()
        self.config.tolerance_for_gathering_ratio = self.tolerance_for_gathering_ratio.value()
        self.config.gathering_debug = self.gathering_debug.isChecked()

        self.config.tolerance_for_player = self.tolerance_for_player.value()
        self.config.tolerance_for_player_ratio = self.tolerance_for_player_ratio.value()
        self.config.player_color_hex = self.current_player_color.name()
        self.config.player_debug = self.player_debug.isChecked()

        self.config.telegram_bot_token = self.telegram_token.text()
        self.config.telegram_chat_id = self.telegram_chat_id.text()

        self.config.radar_enabled = self.radar_enabled.isChecked()
        self.config.radar_binary_path = self.radar_path_edit.text()
        self.config.exit_template_path = self.exit_path_edit.text()
        self.config.vk_invis = self.vk_invis.value()
        self.config.player_danger_radius = self.danger_radius.value()
        self.config.chat_response_chance = self.chat_chance.value()

        self.config.debug = self.debug_checkbox.isChecked()

        if self.config.radar_enabled:
            import os
            if os.path.exists(self.config.radar_binary_path):
                self._radar_proc = subprocess.Popen(
                    [self.config.radar_binary_path],
                    creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
                )
                self.logs.append(f"OpenRadar запущено (PID {self._radar_proc.pid})")

        self.worker = BotWorker(self.config)
        self.worker.log.connect(self.logs.append)
        self.worker.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def stop_bot(self):
        if self.worker:
            self.worker.stop()
            self.logs.append("Зупинено")
        if self._radar_proc:
            self._radar_proc.terminate()
            self._radar_proc = None
            self.logs.append("OpenRadar зупинено")

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
