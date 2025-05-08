import logging
import sys
from PyQt5.QtWidgets import QApplication

from app.core.logging_config import setup_logging
from app.ui.main_window import MainApp


def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("app startup")

    app = QApplication(sys.argv)
    main_window = MainApp()
    main_window.show()
    exit_code = app.exec_()
    logger.info("app closed with exit code %s", exit_code)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
