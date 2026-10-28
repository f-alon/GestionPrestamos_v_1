import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from qfluentwidgets import setTheme, Theme, setThemeColor

from database import init_db
from database.seed import seed_demo_data_if_empty
from ui.main_window import MainWindow


def main():
    # Initialize SQLite database and tables
    init_db()

    # Seed demo data if database is empty for immediate testing
    seed_demo_data_if_empty()

    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)

    # Set Application Icon
    from config import BASE_DIR
    from PySide6.QtGui import QIcon
    icon_path = BASE_DIR / "resources" / "app_icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Set Fluent Theme & Accent Color
    setTheme(Theme.LIGHT)
    setThemeColor("#0078D4")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
