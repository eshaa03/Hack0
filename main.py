import os
import sys

from PyQt5.QtWidgets import QApplication

from frontend.views.base_window import apply_global_theme
from frontend.views.login_window import LoginWindow


def main() -> int:
    app = QApplication(sys.argv)
    apply_global_theme(app)

    window = LoginWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
    raise SystemExit(main())
