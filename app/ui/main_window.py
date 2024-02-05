import os

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from app.threads.download_thread import DownloadingThread

# MainApp builds the simple downloader GUI window.
# It validates user inputs, starts DownloadingThread, and updates the UI through thread signals.

class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.download_thread = None
        self.setWindowTitle("Phoenix Downloader")
        self.resize(750, 320)
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        title_label = QLabel("YouTube Video Downloader - First Build")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)

        url_label = QLabel("Video URL")
        main_layout.addWidget(url_label)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.youtube.com/watch?v=...")
        main_layout.addWidget(self.url_input)

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

        self.progressBar = QProgressBar()
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(0)
        main_layout.addWidget(self.progressBar)

        self.status_label = QLabel("Ready")
        main_layout.addWidget(self.status_label)

        self.downloadButton = QPushButton("Download Video")
        self.downloadButton.clicked.connect(self.Handle_download)
        main_layout.addWidget(self.downloadButton)

    def Handle_location(self):
        folder = QFileDialog.getExistingDirectory(self, "Select save folder", self.path_input.text())
        if folder:
            self.path_input.setText(folder)

    def Handle_download(self):
        url = self.url_input.text().strip()
        save_dir = self.path_input.text().strip()

        if url == "":
            QMessageBox.warning(self, "URL Needed", "Enter YouTube URL first")
            return

        if ("youtube.com" not in url) and ("youtu.be" not in url):
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid YouTube URL")
            return

        if not os.path.isdir(save_dir):
            QMessageBox.warning(self, "Invalid Folder", "Choose a valid save folder")
            return

        self.progressBar.setValue(0)
        self.status_label.setText("Starting download...")
        self.downloadButton.setEnabled(False)

        self.download_thread = DownloadingThread(url, save_dir)
        self.download_thread.progress_changed.connect(self.Update_progress)
        self.download_thread.status_changed.connect(self.Update_status)
        self.download_thread.download_finished.connect(self.Download_finished)
        self.download_thread.download_failed.connect(self.Download_failed)
        self.download_thread.start()

    def Update_progress(self, value):
        self.progressBar.setValue(value)

    def Update_status(self, text):
        self.status_label.setText(text)

    def Download_finished(self, save_dir):
        self.status_label.setText("Download completed")
        self.downloadButton.setEnabled(True)
        QMessageBox.information(self, "Success", f"Video downloaded to:\n{save_dir}")

    def Download_failed(self, error_text):
        self.status_label.setText("Download failed")
        self.downloadButton.setEnabled(True)
        QMessageBox.critical(self, "Error", f"Download failed:\n{error_text}")
