import os
import sys
import subprocess
import time

from app import config
from app.AppEnter import AppEnterService


def main():
    radar_proc = None

    if config.RADAR_BINARY_PATH and os.path.exists(config.RADAR_BINARY_PATH):
        flags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
        radar_proc = subprocess.Popen([config.RADAR_BINARY_PATH], creationflags=flags)
        print(f"[main] OpenRadar запущено PID={radar_proc.pid}, чекаємо 3с...")
        time.sleep(3.0)
    else:
        print("[main] OpenRadar не знайдено — продовжуємо без радару")

    bot = AppEnterService(
        bober_example_path="bobberExamples/bobberExample2.png",
        anchor_example_path="MountHealthBar/MountHealthBar.png",
        exit_template_path="exitExamples/exit.png",
    )

    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n[main] Зупинено")
    finally:
        if radar_proc is not None:
            radar_proc.terminate()
            print("[main] OpenRadar зупинено")


if __name__ == "__main__":
    main()
