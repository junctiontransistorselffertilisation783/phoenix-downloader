import sys
from PyQt5.QtWidgets import *

from app.ui.main_window import MainApp

def main():
    app = QApplication(sys.argv)
    main_window = MainApp()
    main_window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
