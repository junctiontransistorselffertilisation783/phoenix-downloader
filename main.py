# Importing necessary PyQt modules for building the GUI
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# Importing other required libraries
import os
import sys


# MainApp class for the first build phase GUI only
class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phoenix Downloader")
        self.resize(750, 320)
        self.init_ui()

    # Method to initialize the interface widgets and layout
    def init_ui(self):
        # Create central widget for QMainWindow
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main vertical layout
        main_layout = QVBoxLayout(central_widget)

        # Title label
        title_label = QLabel("YouTube Video Downloader - First Build")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)

        # URL input section
        url_label = QLabel("Video URL")
        main_layout.addWidget(url_label)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.youtube.com/watch?v=...")
        main_layout.addWidget(self.url_input)

        # Save location section
        folder_label = QLabel("Save Folder")
        main_layout.addWidget(folder_label)

        folder_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setText(os.path.join(os.path.expanduser("~"), "Downloads"))
        folder_layout.addWidget(self.path_input)

        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.Handle_location)
        folder_layout.addWidget(browse_btn)

        main_layout.addLayout(folder_layout)

        # Progress bar for test display only
        self.progressBar = QProgressBar()
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(0)
        main_layout.addWidget(self.progressBar)

        # Status display label
        self.status_label = QLabel("Ready")
        main_layout.addWidget(self.status_label)

        # Download button for GUI test
        self.downloadButton = QPushButton("Download Video")
        self.downloadButton.clicked.connect(self.Handle_download)
        main_layout.addWidget(self.downloadButton)

    # Method to handle selecting save location
    def Handle_location(self):
        folder = QFileDialog.getExistingDirectory(self, "Select save folder", self.path_input.text())
        if folder:
            self.path_input.setText(folder)

    # \test the download flow in GUI only
    def Handle_download(self):
        url = self.url_input.text().strip()
        save_dir = self.path_input.text().strip()

        # URL validation
        if url == "":
            QMessageBox.warning(self, "URL Needed", "Enter YouTube URL first")
            return

        # Basic youtube domain check for first phase
        if ("youtube.com" not in url) and ("youtu.be" not in url):
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid YouTube URL")
            return

        # Save folder validation
        if not os.path.isdir(save_dir):
            QMessageBox.warning(self, "Invalid Folder", "Choose a valid save folder")
            return

        self.progressBar.setValue(35)
        self.status_label.setText("GUI flow works just tested")

def main():
    app = QApplication(sys.argv)
    main_window = MainApp()
    main_window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
