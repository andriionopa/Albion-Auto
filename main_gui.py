import sys

from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)

    try:
        with open("gui/style.qss", "r") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        pass

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
