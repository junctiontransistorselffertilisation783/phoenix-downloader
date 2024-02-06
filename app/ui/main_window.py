import os

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from app.threads.download_thread import DownloadingThread
from app.threads.get_info_thread import DownloadInfoThread

# MainApp builds the simple downloader GUI window.
# It validates user inputs, starts DownloadingThread, and updates the UI through thread signals.

class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.download_thread = None
        self.info_thread = None
        self.video_info_loaded = False
        self.setWindowTitle("Phoenix Downloader")
        self.resize(860, 560)
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
        self.url_input.textChanged.connect(self.Reset_video_info)
        main_layout.addWidget(self.url_input)

        self.get_info_btn = QPushButton("Get Video Info")
        self.get_info_btn.clicked.connect(self.Handle_get_video_info)
        main_layout.addWidget(self.get_info_btn)

        self.video_title_label = QLabel("Title: -")
        self.video_title_label.setWordWrap(True)
        main_layout.addWidget(self.video_title_label)

        self.video_duration_label = QLabel("Duration: -")
        main_layout.addWidget(self.video_duration_label)

        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(320, 180)
        self.thumbnail_label.setStyleSheet("border: 1px solid #999;")
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setText("Thumbnail")
        main_layout.addWidget(self.thumbnail_label)

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

        quality_label = QLabel("Video Quality")
        main_layout.addWidget(quality_label)

        self.quality_comboBox = QComboBox()
        self.quality_comboBox.addItem("Load video info first")
        main_layout.addWidget(self.quality_comboBox)

        self.progressBar = QProgressBar()
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(0)
        main_layout.addWidget(self.progressBar)

        self.status_label = QLabel("Ready")
        main_layout.addWidget(self.status_label)

        self.downloadButton = QPushButton("Download Video")
        self.downloadButton.clicked.connect(self.Handle_download)
        self.downloadButton.setEnabled(False)
        main_layout.addWidget(self.downloadButton)

    def Reset_video_info(self):
        self.video_info_loaded = False
        self.downloadButton.setEnabled(False)
        self.quality_comboBox.clear()
        self.quality_comboBox.addItem("Load video info first")
        self.video_title_label.setText("Title: -")
        self.video_duration_label.setText("Duration: -")
        self.thumbnail_label.clear()
        self.thumbnail_label.setText("Thumbnail")

    def Handle_location(self):
        folder = QFileDialog.getExistingDirectory(self, "Select save folder", self.path_input.text())
        if folder:
            self.path_input.setText(folder)

    def Handle_get_video_info(self):
        url = self.url_input.text().strip()

        if url == "":
            QMessageBox.warning(self, "URL Needed", "Enter YouTube URL first")
            return

        if ("youtube.com" not in url) and ("youtu.be" not in url):
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid YouTube URL")
            return

        self.status_label.setText("Loading video info...")
        self.get_info_btn.setEnabled(False)
        self.downloadButton.setEnabled(False)

        self.info_thread = DownloadInfoThread(url)
        self.info_thread.vidoes_info.connect(self.Handle_video_info)
        self.info_thread.info_failed.connect(self.Handle_info_failed)
        self.info_thread.start()

    def Handle_video_info(self, data):
        self.get_info_btn.setEnabled(True)

        title = data.get("title", "-")
        duration_text = data.get("duration_text", "-")
        thumbnail_data = data.get("thumbnail_data", None)
        quality_items = data.get("quality_items", [])

        self.video_title_label.setText(f"Title: {title}")
        self.video_duration_label.setText(f"Duration: {duration_text}")

        self.thumbnail_label.clear()
        if thumbnail_data:
            pixmap = QPixmap()
            pixmap.loadFromData(thumbnail_data)
            self.thumbnail_label.setPixmap(pixmap)

        self.quality_comboBox.clear()
        for item in quality_items:
            label = item.get("label", "")
            format_code = item.get("format", "")
            self.quality_comboBox.addItem(label, format_code)

        if self.quality_comboBox.count() > 0:
            for i in range(self.quality_comboBox.count()):
                txt = self.quality_comboBox.itemText(i)
                if txt.startswith("720p"):
                    self.quality_comboBox.setCurrentIndex(i)
                    break

        self.video_info_loaded = True
        self.downloadButton.setEnabled(True)
        self.status_label.setText("Video info loaded")

    def Handle_info_failed(self, error_text):
        self.get_info_btn.setEnabled(True)
        self.video_info_loaded = False
        self.downloadButton.setEnabled(False)
        self.status_label.setText("Failed to load video info")
        QMessageBox.critical(self, "Error", f"Could not load video info:\n{error_text}")

    def Handle_download(self):
        url = self.url_input.text().strip()
        save_dir = self.path_input.text().strip()
        quality = self.quality_comboBox.currentData()
        if quality is None or quality == "":
            quality = self.quality_comboBox.currentText().strip()

        if url == "":
            QMessageBox.warning(self, "URL Needed", "Enter YouTube URL first")
            return

        if ("youtube.com" not in url) and ("youtu.be" not in url):
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid YouTube URL")
            return

        if not os.path.isdir(save_dir):
            QMessageBox.warning(self, "Invalid Folder", "Choose a valid save folder")
            return

        if not self.video_info_loaded:
            QMessageBox.warning(self, "Video Info Needed", "Click Get Video Info first")
            return

        self.progressBar.setValue(0)
        self.status_label.setText("Starting download...")
        self.downloadButton.setEnabled(False)

        self.download_thread = DownloadingThread(url, save_dir, quality)
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
        self.get_info_btn.setEnabled(True)
        QMessageBox.information(self, "Success", f"Video downloaded to:\n{save_dir}")

    def Download_failed(self, error_text):
        self.status_label.setText("Download failed")
        self.downloadButton.setEnabled(True)
        self.get_info_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", f"Download failed:\n{error_text}")
