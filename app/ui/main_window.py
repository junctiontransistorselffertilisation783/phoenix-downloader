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
        self.is_downloading = False
        self.settings = QSettings("PhoenixDownloader", "PhoenixDownloaderApp")
        self.setWindowTitle("Phoenix Downloader")
        self.resize(860, 560)
        self.init_ui()
        self.Load_saved_data()

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

        self.url_input = QComboBox()
        self.url_input.setEditable(True)
        self.url_input.setInsertPolicy(QComboBox.NoInsert)
        self.url_input.setMaxVisibleItems(10)
        # self.url_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.url_input.setCurrentText("")
        self.url_input.lineEdit().setPlaceholderText("https://www.youtube.com/watch?v=...")
        self.url_input.lineEdit().returnPressed.connect(self.Handle_get_video_info)
        self.url_input.editTextChanged.connect(self.Reset_video_info)
        self.url_completer = self.url_input.completer()
        self.url_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.url_completer.setCompletionMode(QCompleter.PopupCompletion)
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
        self.thumbnail_label.setScaledContents(True)
        self.thumbnail_label.setText("Thumbnail")
        thumbnail_layout = QHBoxLayout()
        thumbnail_layout.addStretch()
        thumbnail_layout.addWidget(self.thumbnail_label)
        thumbnail_layout.addStretch()
        main_layout.addLayout(thumbnail_layout)

        folder_label = QLabel("Save Folder")
        main_layout.addWidget(folder_label)

        folder_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setText(self.Get_default_folder())
        folder_layout.addWidget(self.path_input)

        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self.Handle_location)
        folder_layout.addWidget(self.browse_btn)

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

        self.cancelButton = QPushButton("Cancel Download")
        self.cancelButton.clicked.connect(self.Handle_cancel_download)
        self.cancelButton.setEnabled(False)
        main_layout.addWidget(self.cancelButton)

    def Reset_video_info(self):
        if self.is_downloading:
            return

        self.video_info_loaded = False
        self.downloadButton.setEnabled(False)
        self.cancelButton.setEnabled(False)
        self.quality_comboBox.clear()
        self.quality_comboBox.addItem("Load video info first")
        self.video_title_label.setText("Title: -")
        self.video_duration_label.setText("Duration: -")
        self.thumbnail_label.clear()
        self.thumbnail_label.setText("Thumbnail")

    def Get_url_text(self):
        return self.url_input.currentText().strip()

    def Get_default_folder(self):
        saved_folder = self.settings.value("last_folder", "")
        if saved_folder and os.path.isdir(saved_folder):
            return saved_folder

        return os.path.join(os.path.expanduser("~"), "Downloads")

    def Load_saved_data(self):
        saved_urls = self.settings.value("recent_urls", [], type=list)
        if saved_urls is None:
            saved_urls = []

        self.url_input.clear()
        for url in saved_urls:
            if url:
                self.url_input.addItem(url)

        self.url_input.setCurrentText("")

        saved_folder = self.settings.value("last_folder", "")
        if saved_folder and os.path.isdir(saved_folder):
            self.path_input.setText(saved_folder)

    def Save_folder_history(self):
        folder = self.path_input.text().strip()
        if folder != "":
            self.settings.setValue("last_folder", folder)

    def Save_url_history(self, url):
        if url == "":
            return

        saved_urls = self.settings.value("recent_urls", [], type=list)
        if saved_urls is None:
            saved_urls = []

        saved_urls = [saved_url for saved_url in saved_urls if saved_url != url]
        saved_urls.insert(0, url)
        saved_urls = saved_urls[:15]

        self.settings.setValue("recent_urls", saved_urls)

        self.url_input.clear()
        for saved_url in saved_urls:
            self.url_input.addItem(saved_url)
        self.url_input.setCurrentText(url)

    def Handle_location(self):
        folder = QFileDialog.getExistingDirectory(self, "Select save folder", self.path_input.text())
        if folder:
            self.path_input.setText(folder)
            self.Save_folder_history()

    def Handle_get_video_info(self):
        if self.is_downloading:
            QMessageBox.warning(self, "Download Running", "Cancel the current download first")
            return

        url = self.Get_url_text()

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
        self.Save_url_history(self.Get_url_text())

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
        else:
            self.thumbnail_label.setText("Thumbnail")

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
        url = self.Get_url_text()
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

        self.Save_folder_history()

        if not self.video_info_loaded:
            QMessageBox.warning(self, "Video Info Needed", "Click Get Video Info first")
            return

        self.progressBar.setValue(0)
        self.status_label.setText("Starting download...")
        self.is_downloading = True
        self.downloadButton.setEnabled(False)
        self.get_info_btn.setEnabled(False)
        self.cancelButton.setEnabled(True)
        self.url_input.setEnabled(False)
        self.path_input.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.quality_comboBox.setEnabled(False)

        self.download_thread = DownloadingThread(url, save_dir, quality)
        self.download_thread.progress_changed.connect(self.Update_progress)
        self.download_thread.status_changed.connect(self.Update_status)
        self.download_thread.download_finished.connect(self.Download_finished)
        self.download_thread.download_failed.connect(self.Download_failed)
        self.download_thread.download_cancelled.connect(self.Download_cancelled)
        self.download_thread.start()

    def Handle_cancel_download(self):
        if self.download_thread and self.download_thread.isRunning():
            self.status_label.setText("Cancelling download...")
            self.cancelButton.setEnabled(False)
            self.download_thread.Cancel_download()

    def Update_progress(self, value):
        self.progressBar.setValue(value)

    def Update_status(self, text):
        self.status_label.setText(text)

    def Download_finished(self, save_dir):
        self.Save_url_history(self.Get_url_text())
        self.is_downloading = False
        self.download_thread = None
        self.status_label.setText("Download completed")
        self.downloadButton.setEnabled(True)
        self.get_info_btn.setEnabled(True)
        self.cancelButton.setEnabled(False)
        self.url_input.setEnabled(True)
        self.path_input.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.quality_comboBox.setEnabled(True)
        QMessageBox.information(self, "Success", f"Video downloaded to:\n{save_dir}")

    def Download_failed(self, error_text):
        self.is_downloading = False
        self.download_thread = None
        self.status_label.setText("Download failed")
        self.downloadButton.setEnabled(True)
        self.get_info_btn.setEnabled(True)
        self.cancelButton.setEnabled(False)
        self.url_input.setEnabled(True)
        self.path_input.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.quality_comboBox.setEnabled(True)
        QMessageBox.critical(self, "Error", f"Download failed:\n{error_text}")

    def Download_cancelled(self):
        self.is_downloading = False
        self.download_thread = None
        self.status_label.setText("Download cancelled")
        self.progressBar.setValue(0)
        self.downloadButton.setEnabled(True)
        self.get_info_btn.setEnabled(True)
        self.cancelButton.setEnabled(False)
        self.url_input.setEnabled(True)
        self.path_input.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.quality_comboBox.setEnabled(True)
