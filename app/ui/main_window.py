import os
import re

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from app.threads.download_thread import DownloadingThread
from app.threads.get_info_thread import DownloadInfoThread
from app.ui.ui_downloader import Ui_MainWindow
from app.ytdlp.core import build_quality_format


class MainApp(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.download_thread = None
        self.info_thread = None
        self.video_info_loaded = False
        self.current_info_type = "video"
        self.is_downloading = False
        self.playlist_entries = []
        self.playlist_title = ""
        self.selected_playlist_entry = None
        self.current_video_language = "unknown"
        self.last_loaded_url = ""
        self.default = True
        self.settings = QSettings("PhoenixDownloader", "PhoenixDownloaderApp")
        self.auto_info_timer = QTimer(self)
        self.auto_info_timer.setSingleShot(True)
        self.auto_info_timer.timeout.connect(self.Handle_auto_get_video_info)
        self.init_ui()
        self.Load_saved_data()
        self.Reset_video_info()

    def init_ui(self):
        self.setupUi(self)

        self.url_input = self.url_line
        self.path_input = self.location_line
        self.get_info_btn = self.searchButton
        self.browse_btn = self.browseButton
        self.quality_comboBox = self.Quality_comboBox
        self.subtitle_checkBox = self.Subtitles_checkBox
        self.chapters_checkBox = self.Chapters_chehkBox
        self.thumbnail_label = self.Thumbnail_label
        self.status_label = self.Display_videoName
        self.progress_details_label = self.label_4

        self.quality_label = self.label_3
        self.info_group = self.Thumbnail_label

        self.cancelButton = QPushButton("Cancel", self.centralwidget)
        self.cancelButton.setGeometry(QRect(390, 470, 170, 36))
        self.cancelButton.hide()

        btn_font = QFont()
        btn_font.setPointSize(11)
        btn_font.setBold(True)
        self.downloadButton.setFont(btn_font)
        self.downloadButton.setGeometry(QRect(390, 470, 170, 36))
        self.cancelButton.setFont(btn_font)

        self.downloadButton.setStyleSheet(
            "QPushButton:disabled {"
            " background-color: #3a4556;"
            " color: #8f9aaa;"
            "}"
        )

        status_font = QFont()
        status_font.setPointSize(10)
        status_font.setBold(False)
        self.status_label.setFont(status_font)

        self.downloadButton.clicked.connect(self.Handle_download)
        self.cancelButton.clicked.connect(self.Handle_cancel_download)
        self.searchButton.pressed.connect(self.Defulat_fun)
        self.get_info_btn.clicked.connect(self.Handle_get_video_info)
        self.browse_btn.clicked.connect(self.Handle_location)
        self.Playlist_comboBox.currentIndexChanged.connect(self.Handle_playlist_selection)
        self.AdvancedOptions_checkBox.clicked.connect(self.Adv_UI_Setup)
        self.Plst_Range_checkBox.clicked.connect(self.Adv_UI_Setup)
        self.Add_Prefix_checkBox.clicked.connect(self.Adv_UI_Setup)
        self.Add_Suffix_checkBox.clicked.connect(self.Adv_UI_Setup)
        self.Range_save_pushButton.clicked.connect(self.Adv_UI_Setup)

        self.url_input.lineEdit().returnPressed.connect(self.Handle_get_video_info)
        self.url_input.editTextChanged.connect(self.Handle_url_text_changed)
        self.url_completer = self.url_input.completer()
        self.url_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.url_completer.setCompletionMode(QCompleter.PopupCompletion)

        self.path_input.lineEdit().setPlaceholderText("Select download folder")
        self.path_input.setCurrentText(self.Get_default_folder())
        self.path_completer = self.path_input.completer()
        self.path_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.path_completer.setCompletionMode(QCompleter.PopupCompletion)

        self.downloadButton.setEnabled(False)

        self.playlist_num_display.hide()
        self.Playlist_comboBox.hide()
        self.Plst_Range_frame.hide()
        self.Suffix_lineEdit.hide()
        self.label_4.hide()
        self.v_options_groupBox.hide()
        self.plst_options_groupBox.hide()
        self.prefix_no_cmbx.show()

    def Defulat_fun(self):
        self.default = False
        self.Playlist_comboBox.setCurrentIndex(0)

    def Adv_UI_Setup(self):
        checkbox = self.sender()

        if checkbox == self.AdvancedOptions_checkBox:
            if self.AdvancedOptions_checkBox.isChecked():
                self.v_options_groupBox.show()
                self.plst_options_groupBox.show()
                self.line.hide()
                self.resize(self.width(), self.height() + 150)
            else:
                self.v_options_groupBox.hide()
                self.plst_options_groupBox.hide()
                self.line.show()
                self.resize(self.width(), self.height() - 150)

        elif checkbox == self.Plst_Range_checkBox:
            if self.Plst_Range_checkBox.isChecked():
                self.Plst_Range_frame.show()
                self.CurrentVideo_checkBox.hide()
            else:
                self.Plst_Range_frame.hide()
                self.CurrentVideo_checkBox.show()

        elif checkbox == self.Range_save_pushButton:
            start = self.Range_start_spnbx.value()
            end = self.Range_end_spnbx.value()
            if end >= start:
                self.Items_Range_cmbx.insertItem(0, f"{start}-{end}")
                self.Items_Range_cmbx.setCurrentIndex(0)

        elif checkbox == self.Add_Prefix_checkBox:
            if self.Add_Prefix_checkBox.isChecked():
                self.prefix_no_cmbx.show()
                self.Add_Prefix_checkBox.setText("Add")
            else:
                self.prefix_no_cmbx.hide()
                self.Add_Prefix_checkBox.setText("Add Prefix-Plst_No")

        elif checkbox == self.Add_Suffix_checkBox:
            if self.Add_Suffix_checkBox.isChecked():
                self.Suffix_lineEdit.show()
                self.Add_Suffix_checkBox.setText("")
            else:
                self.Suffix_lineEdit.hide()
                self.Add_Suffix_checkBox.setText("Add Suffix")

    def Set_download_controls(self, downloading):
        if downloading:
            self.downloadButton.hide()
            self.cancelButton.show()
            self.cancelButton.setEnabled(True)
        else:
            self.cancelButton.hide()
            self.cancelButton.setEnabled(False)
            self.downloadButton.show()

    def Set_inputs_enabled(self, enabled):
        self.get_info_btn.setEnabled(enabled)
        self.url_input.setEnabled(enabled)
        self.path_input.setEnabled(enabled)
        self.browse_btn.setEnabled(enabled)
        self.quality_comboBox.setEnabled(enabled)
        self.subtitle_checkBox.setEnabled(enabled)
        self.chapters_checkBox.setEnabled(enabled)
        self.Playlist_comboBox.setEnabled(enabled)

    def Get_url_text(self):
        return self.url_input.currentText().strip()

    def Get_save_path_text(self):
        return self.path_input.currentText().strip()

    def Get_default_folder(self):
        saved_folder = self.settings.value("last_folder", "")
        if saved_folder and os.path.isdir(saved_folder):
            return saved_folder

        return os.path.join(os.path.expanduser("~"), "Downloads")

    def Load_saved_data(self):
        saved_urls = self.settings.value("recent_urls", [], type=list)
        if saved_urls is None:
            saved_urls = []

        self.url_input.blockSignals(True)
        self.url_input.clear()
        for url in saved_urls:
            if url:
                self.url_input.addItem(url)
        self.url_input.setCurrentText("")
        self.url_input.blockSignals(False)

        saved_paths = self.settings.value("recent_paths", [], type=list)
        if saved_paths is None:
            saved_paths = []

        default_folder = self.Get_default_folder()
        if default_folder not in saved_paths:
            saved_paths.insert(0, default_folder)

        self.path_input.blockSignals(True)
        self.path_input.clear()
        for folder in saved_paths[:15]:
            if folder:
                self.path_input.addItem(folder)
        self.path_input.setCurrentText(default_folder)
        self.path_input.blockSignals(False)

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

        self.url_input.blockSignals(True)
        self.url_input.clear()
        for saved_url in saved_urls:
            self.url_input.addItem(saved_url)
        self.url_input.setCurrentText(url)
        self.url_input.blockSignals(False)

    def Save_folder_history(self):
        folder = self.Get_save_path_text()
        if folder == "":
            return

        self.settings.setValue("last_folder", folder)

        saved_paths = self.settings.value("recent_paths", [], type=list)
        if saved_paths is None:
            saved_paths = []

        saved_paths = [saved_path for saved_path in saved_paths if saved_path != folder]
        saved_paths.insert(0, folder)
        saved_paths = saved_paths[:15]
        self.settings.setValue("recent_paths", saved_paths)

        self.path_input.blockSignals(True)
        self.path_input.clear()
        for saved_path in saved_paths:
            self.path_input.addItem(saved_path)
        self.path_input.setCurrentText(folder)
        self.path_input.blockSignals(False)

    def Handle_location(self):
        folder = QFileDialog.getExistingDirectory(self, "Select save folder", self.Get_save_path_text())
        if folder:
            self.path_input.setCurrentText(folder)
            self.Save_folder_history()

    def Detect_url_type(self, url):
        url = url.lower()
        if "list=" in url:
            return "playlist"
        return "video"

    def Is_youtube_url(self, url):
        url = str(url or "")
        return ("youtube.com" in url) or ("youtu.be" in url)

    def Set_thumbnail_data(self, thumbnail_data):
        self.thumbnail_label.clear()

        if thumbnail_data:
            pixmap = QPixmap()
            pixmap.loadFromData(thumbnail_data)
            pixmap = pixmap.scaled(self.thumbnail_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.thumbnail_label.setPixmap(pixmap)
        else:
            self.thumbnail_label.setPixmap(QPixmap())

    def Load_quality_items(self, quality_items, preferred_texts=None):
        self.quality_comboBox.clear()

        for item in quality_items:
            label = item.get("label", "")
            format_code = item.get("format", "")
            self.quality_comboBox.addItem(label, format_code)

        if self.quality_comboBox.count() == 0:
            return

        selected_index = -1
        for i in range(self.quality_comboBox.count()):
            text = self.quality_comboBox.itemText(i).lower()
            if ("480p" in text) or ("x480" in text) or (" 480 " in text):
                selected_index = i
                break

        if selected_index >= 0:
            self.quality_comboBox.setCurrentIndex(selected_index)
            return

        if self.current_info_type == "playlist":
            for i in range(self.quality_comboBox.count()):
                text = self.quality_comboBox.itemText(i).lower()
                if ("360p" in text) or ("x360" in text) or (" 360 " in text):
                    self.quality_comboBox.setCurrentIndex(i)
                    return

        if preferred_texts:
            for preferred_text in preferred_texts:
                preferred_low = preferred_text.lower()
                for i in range(self.quality_comboBox.count()):
                    text = self.quality_comboBox.itemText(i).lower()
                    if text.startswith(preferred_low) or (preferred_low in text):
                        self.quality_comboBox.setCurrentIndex(i)
                        return

        self.quality_comboBox.setCurrentIndex(0)

    def Set_mode_layout(self, info_type):
        self.current_info_type = info_type

        if info_type == "playlist":
            self.playlist_num_display.show()
            self.Playlist_comboBox.show()
            self.quality_label.setText("Quality")
        elif info_type == "video":
            self.playlist_num_display.hide()
            self.Playlist_comboBox.hide()
            self.quality_label.setText("Quality")
        else:
            self.playlist_num_display.hide()
            self.Playlist_comboBox.hide()

    def Update_download_button_text(self):
        if self.current_info_type == "playlist":
            self.downloadButton.setText("Download Playlist")
            return
        self.downloadButton.setText("Download Video")

    def Set_empty_info_state(self):
        self.playlist_entries = []
        self.playlist_title = ""
        self.selected_playlist_entry = None
        self.current_video_language = "unknown"
        self.video_info_loaded = False
        self.Set_mode_layout("empty")
        self.info_group.hide()
        self.downloadButton.setEnabled(False)
        self.Set_download_controls(False)
        self.quality_comboBox.clear()
        self.Playlist_comboBox.clear()
        self.playlist_num_display.clear()
        self.playlist_num_display.hide()
        self.Playlist_comboBox.hide()
        self.progressBar.setValue(0)
        self.status_label.setText("Ready")
        self.progress_details_label.setText("")
        self.Update_download_button_text()

    def Reset_video_info(self):
        if self.is_downloading:
            return
        self.Set_empty_info_state()

    def Handle_url_text_changed(self, _text=""):
        self.Reset_video_info()
        self.Schedule_auto_get_video_info()

    def Schedule_auto_get_video_info(self):
        if self.is_downloading:
            return

        url = self.Get_url_text()
        if not self.Is_youtube_url(url):
            self.auto_info_timer.stop()
            return

        if url == self.last_loaded_url and self.video_info_loaded:
            return

        self.auto_info_timer.start(1200)

    def Handle_auto_get_video_info(self):
        if self.is_downloading:
            return

        url = self.Get_url_text()
        if url == "":
            return

        if not self.Is_youtube_url(url):
            return

        if url == self.last_loaded_url and self.video_info_loaded:
            return

        self.Handle_get_video_info()

    def Populate_playlist_comboBox(self):
        self.Playlist_comboBox.blockSignals(True)
        self.Playlist_comboBox.clear()
        for entry in self.playlist_entries:
            index_value = int(entry.get("index", 0))
            self.Playlist_comboBox.addItem(str(index_value))
        if self.Playlist_comboBox.count() > 0:
            self.Playlist_comboBox.setCurrentIndex(0)
        self.Playlist_comboBox.blockSignals(False)
        self.Handle_playlist_selection()

    def Handle_playlist_selection(self):
        if self.current_info_type != "playlist":
            return

        selected_index = self.Playlist_comboBox.currentIndex()
        if selected_index < 0 or selected_index >= len(self.playlist_entries):
            self.selected_playlist_entry = None
            self.quality_comboBox.clear()
            self.downloadButton.setEnabled(False)
            return

        entry = self.playlist_entries[selected_index]
        self.selected_playlist_entry = entry

        selected_thumbnail = entry.get("thumbnail_data")
        if selected_thumbnail:
            self.Set_thumbnail_data(selected_thumbnail)

        entry_quality_items = entry.get("quality_items", [])
        self.Load_quality_items(entry_quality_items, ["480p", "720p", "Best"])

        entry_title = str(entry.get("title", ""))
        self.status_label.setText(entry_title)
        total_entries = len(self.playlist_entries)
        self.playlist_num_display.setText(f"{selected_index + 1}/{total_entries}")
        self.downloadButton.setEnabled(bool(entry_quality_items))
        self.progress_details_label.setText("Selected video quality will be used for full playlist with fallback")

    def Build_playlist_quality_from_selection(self):
        selected_text = self.quality_comboBox.currentText().strip().lower()
        match = re.search(r"(\d{3,4})p", selected_text)
        if match:
            height_value = int(match.group(1))
            return build_quality_format(f"{height_value}p")

        match = re.search(r"(\d{3,4})x(\d{3,4})", selected_text)
        if match:
            height_value = int(match.group(2))
            if height_value <= 240:
                return build_quality_format("240p")
            if height_value <= 480:
                return build_quality_format("480p")
            if height_value <= 720:
                return build_quality_format("720p")
            return build_quality_format("Best")

        data_value = self.quality_comboBox.currentData()
        if isinstance(data_value, str) and data_value.strip() != "":
            return data_value

        return build_quality_format("720p")

    def Handle_get_video_info(self):
        self.auto_info_timer.stop()
        if self.is_downloading:
            QMessageBox.warning(self, "Download Running", "Cancel the current download first")
            return

        url = self.Get_url_text()
        if url == "":
            QMessageBox.warning(self, "URL Needed", "Enter YouTube URL first")
            return

        if not self.Is_youtube_url(url):
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid YouTube URL")
            return

        url_type = self.Detect_url_type(url)
        self.get_info_btn.setEnabled(False)
        self.downloadButton.setEnabled(False)
        self.status_label.setText("Loading info...")
        self.progress_details_label.setText("Reading media details and available formats")

        self.info_thread = DownloadInfoThread(url, url_type, self.Thumbnail_checkBox.isChecked())
        self.info_thread.vidoes_info.connect(self.Handle_video_info)
        self.info_thread.update_Entreis.connect(self.Handle_playlist_entry_update)
        self.info_thread.info_failed.connect(self.Handle_info_failed)
        self.info_thread.start()

    def Handle_playlist_entry_update(self, entry_update):
        if self.current_info_type != "playlist":
            return

        entry_index = int(entry_update.get("index", 0)) - 1
        if entry_index < 0 or entry_index >= len(self.playlist_entries):
            return

        entry = self.playlist_entries[entry_index]
        quality_items = entry_update.get("quality_items", [])
        if quality_items:
            entry["quality_items"] = quality_items
            entry["is_available"] = True

        updated_title = str(entry_update.get("title", "")).strip()
        if updated_title:
            entry["title"] = updated_title

        duration_seconds = entry_update.get("duration_seconds")
        if isinstance(duration_seconds, int) and duration_seconds > 0:
            entry["duration_seconds"] = duration_seconds

        thumbnail_data = entry_update.get("thumbnail_data")
        if thumbnail_data:
            entry["thumbnail_data"] = thumbnail_data

        if thumbnail_data and entry_index == 0:
            self.Set_thumbnail_data(thumbnail_data)
            self.status_label.setText(str(entry.get("title", self.playlist_title)))
            self.progress_details_label.setText("First video info loaded. continue loading playlist videos in groups of 3")

        selected_index = self.Playlist_comboBox.currentIndex()
        if selected_index == entry_index:
            self.selected_playlist_entry = entry
            if entry.get("thumbnail_data"):
                self.Set_thumbnail_data(entry.get("thumbnail_data"))
            self.Load_quality_items(entry.get("quality_items", []), ["480p", "720p", "Best"])
            self.downloadButton.setEnabled(self.quality_comboBox.count() > 0)

    def Handle_video_info(self, data):
        self.get_info_btn.setEnabled(True)
        self.Save_url_history(self.Get_url_text())
        self.video_info_loaded = True
        self.last_loaded_url = self.Get_url_text()
        self.info_group.show()

        info_type = data.get("info_type", "video")
        title = data.get("title", "-")
        uploader = data.get("uploader", "Unknown channel")
        thumbnail_data = data.get("thumbnail_data", None)

        self.Set_mode_layout(info_type)
        self.Set_thumbnail_data(thumbnail_data)

        if info_type == "playlist":
            self.current_video_language = "unknown"
            self.playlist_title = title
            self.playlist_entries = data.get("entries", [])
            playlist_count = data.get("playlist_count", len(self.playlist_entries))

            self.playlist_num_display.setText("1")
            self.Range_start_spnbx.setMaximum(max(1, int(playlist_count)))
            self.Range_end_spnbx.setMaximum(max(1, int(playlist_count)))
            self.Range_end_spnbx.setValue(max(1, int(playlist_count)))

            if len(self.playlist_entries) > 0:
                first_entry = self.playlist_entries[0]
                first_title = first_entry.get("title", title)
                self.status_label.setText(str(first_title))
                fast_playlist_quality = [
                    {"label": "Best available", "format": build_quality_format("Best")},
                    {"label": "720p", "format": build_quality_format("720p")},
                    {"label": "480p", "format": build_quality_format("480p")},
                    {"label": "240p", "format": build_quality_format("240p")},
                    {"label": "Audio only (139)", "format": build_quality_format("Audio only (139)")},
                ]
                self.Load_quality_items(fast_playlist_quality, ["480p", "720p", "Best"])

            self.Populate_playlist_comboBox()
            self.status_label.setText(str(title))
            self.progress_details_label.setText(f"Playlist loaded: {playlist_count} videos. loading first video info...")
            self.downloadButton.setEnabled(self.Playlist_comboBox.count() > 0 and self.quality_comboBox.count() > 0)
            self.Update_download_button_text()
        else:
            duration_text = data.get("duration_text", "-")
            quality_items = data.get("quality_items", [])
            language = data.get("language", "unknown")
            self.current_video_language = language
            subtitle_profile = data.get("subtitle_profile", {})
            has_subtitles = bool(subtitle_profile.get("has_any", False))
            manual_count = int(subtitle_profile.get("manual_count", 0))
            auto_count = int(subtitle_profile.get("auto_count", 0))
            preferred_available = subtitle_profile.get("preferred_available", [])

            self.status_label.setText(str(title))
            self.Load_quality_items(quality_items, ["480p", "720p", "Best"])
            self.downloadButton.setEnabled(self.quality_comboBox.count() > 0)
            self.subtitle_checkBox.setEnabled(has_subtitles)
            if not has_subtitles:
                self.subtitle_checkBox.setChecked(False)

            subtitle_hint = "Subtitles: none detected"
            if has_subtitles:
                subtitle_hint = f"Subtitles: manual={manual_count}, auto={auto_count}"
                if preferred_available:
                    subtitle_hint = subtitle_hint + f" | preferred found: {', '.join(preferred_available)}"

            self.progress_details_label.setText(f"Channel: {uploader} | Duration: {duration_text} | lang={language} | {subtitle_hint}")
            self.Update_download_button_text()

    def Handle_info_failed(self, error_text):
        self.get_info_btn.setEnabled(True)
        self.video_info_loaded = False
        self.last_loaded_url = ""
        self.downloadButton.setEnabled(False)
        self.status_label.setText("Failed to load info")
        self.progress_details_label.setText("Could not read this URL")
        QMessageBox.critical(self, "Error", f"Could not load video info:\n{error_text}")

    def Build_download_request(self):
        url = self.Get_url_text()
        download_type = "video"
        playlist_title = ""
        quality = self.quality_comboBox.currentData()
        if quality is None or quality == "":
            quality = self.quality_comboBox.currentText().strip()

        if self.current_info_type == "playlist":
            if self.selected_playlist_entry is None:
                raise ValueError("Select playlist video index first")
            download_type = "playlist"
            playlist_title = self.playlist_title
            quality = self.Build_playlist_quality_from_selection()

        return url, download_type, playlist_title, quality

    def Handle_download(self):
        save_dir = self.Get_save_path_text()
        if self.Get_url_text() == "":
            QMessageBox.warning(self, "URL Needed", "Enter YouTube URL first")
            return

        if not os.path.isdir(save_dir):
            QMessageBox.warning(self, "Invalid Folder", "Choose a valid save folder")
            return

        if not self.video_info_loaded:
            QMessageBox.warning(self, "Video Info Needed", "Click Load Video Info first")
            return

        try:
            download_url, download_type, playlist_title, quality = self.Build_download_request()
        except ValueError as error:
            QMessageBox.warning(self, "Download Not Ready", str(error))
            return

        self.Save_folder_history()
        self.progressBar.setValue(0)
        self.status_label.setText("Starting download...")

        if download_type == "playlist":
            self.progress_details_label.setText("Preparing full playlist download with selected quality target")
        else:
            self.progress_details_label.setText("Preparing selected video format")

        self.is_downloading = True
        self.downloadButton.setEnabled(False)
        self.Set_download_controls(True)
        self.Set_inputs_enabled(False)

        self.download_thread = DownloadingThread(
            download_url,
            save_dir,
            quality,
            download_type,
            playlist_title,
            len(self.playlist_entries) if download_type == "playlist" else 0,
            self.Add_Prefix_checkBox.isChecked() if download_type == "playlist" else False,
            self.prefix_no_cmbx.currentIndex() if download_type == "playlist" else 0,
            self.subtitle_checkBox.isChecked(),
            self.chapters_checkBox.isChecked(),
            self.current_video_language,
        )
        self.download_thread.progress_changed.connect(self.Update_progress)
        self.download_thread.status_changed.connect(self.Update_status)
        self.download_thread.details_changed.connect(self.Update_progress_details)
        self.download_thread.download_finished.connect(self.Download_finished)
        self.download_thread.download_failed.connect(self.Download_failed)
        self.download_thread.download_cancelled.connect(self.Download_cancelled)
        self.download_thread.start()

    def Handle_cancel_download(self):
        if self.download_thread and self.download_thread.isRunning():
            self.status_label.setText("Cancelling download...")
            self.progress_details_label.setText("Stopping the active download job")
            self.cancelButton.setEnabled(False)
            self.download_thread.Cancel_download()

    def Update_progress(self, value):
        self.progressBar.setValue(value)

    def Update_status(self, text):
        self.status_label.setText(text)

    def Update_progress_details(self, text):
        self.progress_details_label.setText(text)

    def Download_finished(self, save_dir):
        self.Save_url_history(self.Get_url_text())
        self.is_downloading = False
        self.download_thread = None
        self.status_label.setText("Ready")
        self.progress_details_label.setText("")
        self.downloadButton.setEnabled(False)
        self.Set_download_controls(False)
        self.Set_inputs_enabled(True)
        QMessageBox.information(self, "Success", f"Download saved to:\n{save_dir}")
        self.url_input.setCurrentText("")
        self.last_loaded_url = ""
        self.Set_empty_info_state()

    def Download_failed(self, error_text):
        self.is_downloading = False
        self.download_thread = None
        self.status_label.setText("Download failed")
        self.progress_details_label.setText("The download stopped before the file could be saved")
        self.downloadButton.setEnabled(True)
        self.Set_download_controls(False)
        self.Set_inputs_enabled(True)
        QMessageBox.critical(self, "Error", f"Download failed:\n{error_text}")

    def Download_cancelled(self):
        self.is_downloading = False
        self.download_thread = None
        self.status_label.setText("Download cancelled")
        self.progressBar.setValue(0)
        self.progress_details_label.setText("The active download was cancelled")
        self.downloadButton.setEnabled(True)
        self.Set_download_controls(False)
        self.Set_inputs_enabled(True)
