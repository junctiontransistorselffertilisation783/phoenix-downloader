import os

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from app.threads.download_thread import DownloadingThread
from app.threads.get_info_thread import DownloadInfoThread
from app.ui.ui_downloader import Ui_MainWindow


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
        self.playlist_policy_quality_items = []
        self.selected_playlist_entry = None
        self.default = True
        self.settings = QSettings("PhoenixDownloader", "PhoenixDownloaderApp")
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
        self.thumbnail_label = self.Thumbnail_label
        self.status_label = self.Display_videoName
        self.progress_details_label = self.label_4

        self.quality_label = self.label_3
        self.info_group = self.Thumbnail_label

        self.playlist_action_wrap = QWidget(self.centralwidget)
        self.playlist_action_wrap.setVisible(False)
        self.playlist_action_combo = QComboBox(self.playlist_action_wrap)
        self.playlist_action_combo.addItem("Download selected video", "selected")
        self.playlist_action_combo.addItem("Download full playlist", "playlist")

        self.playlist_preview_list = QListWidget(self.centralwidget)
        self.playlist_preview_list.setGeometry(QRect(630, 180, 255, 182))
        self.playlist_preview_list.hide()

        self.info_type_label = QLabel(self.centralwidget)
        self.video_title_label = QLabel(self.centralwidget)
        self.video_duration_label = QLabel(self.centralwidget)
        self.info_hint_label = QLabel(self.centralwidget)
        self.playlist_count_value = QLabel(self.centralwidget)
        self.playlist_total_duration_value = QLabel(self.centralwidget)
        self.playlist_selected_value = QLabel(self.centralwidget)

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
        self.playlist_action_combo.currentIndexChanged.connect(self.Handle_playlist_action_changed)
        self.playlist_preview_list.itemSelectionChanged.connect(self.Handle_playlist_selection)
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
        self.playlist_action_combo.setEnabled(enabled)
        self.subtitle_checkBox.setEnabled(enabled)
        self.playlist_preview_list.setEnabled(enabled)

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

        if preferred_texts:
            for preferred_text in preferred_texts:
                for i in range(self.quality_comboBox.count()):
                    if self.quality_comboBox.itemText(i).startswith(preferred_text):
                        self.quality_comboBox.setCurrentIndex(i)
                        return

    def Set_mode_layout(self, info_type):
        self.current_info_type = info_type

        if info_type == "playlist":
            self.playlist_action_wrap.show()
            self.playlist_preview_list.show()
            self.playlist_count_value.show()
            self.playlist_total_duration_value.show()
            self.playlist_selected_value.show()
            self.quality_label.setText("Quality")
        elif info_type == "video":
            self.playlist_action_wrap.hide()
            self.playlist_preview_list.hide()
            self.playlist_count_value.hide()
            self.playlist_total_duration_value.hide()
            self.playlist_selected_value.hide()
            self.quality_label.setText("Quality")
        else:
            self.playlist_action_wrap.hide()
            self.playlist_preview_list.hide()
            self.playlist_count_value.hide()
            self.playlist_total_duration_value.hide()
            self.playlist_selected_value.hide()

    def Update_download_button_text(self):
        if self.current_info_type == "playlist":
            if self.playlist_action_combo.currentData() == "playlist":
                self.downloadButton.setText("Download Playlist")
            else:
                self.downloadButton.setText("Download Selected Video")
        else:
            self.downloadButton.setText("Download Video")

    def Set_empty_info_state(self):
        self.playlist_entries = []
        self.playlist_title = ""
        self.playlist_policy_quality_items = []
        self.selected_playlist_entry = None
        self.video_info_loaded = False
        self.Set_mode_layout("empty")
        self.info_group.hide()
        self.downloadButton.setEnabled(False)
        self.Set_download_controls(False)
        self.quality_comboBox.clear()
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

    def Populate_playlist_entries(self, entries):
        self.playlist_preview_list.clear()
        first_ready_row = -1

        for row_index, entry in enumerate(entries):
            prefix = f"{entry.get('index', 0):02d}"
            title = entry.get("title", "-")
            duration_text = entry.get("duration_text", "Unknown")
            availability = "Ready" if entry.get("is_available", False) else "Unavailable"
            item_text = f"{prefix}  |  {title}  |  {duration_text}  |  {availability}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, row_index)

            if not entry.get("is_available", False):
                item.setForeground(QColor("#777777"))
            elif first_ready_row == -1:
                first_ready_row = row_index

            self.playlist_preview_list.addItem(item)

        if first_ready_row >= 0:
            self.playlist_preview_list.setCurrentRow(first_ready_row)
        elif self.playlist_preview_list.count() > 0:
            self.playlist_preview_list.setCurrentRow(0)

    def Refresh_playlist_quality_mode(self):
        if self.current_info_type != "playlist":
            return

        action = self.playlist_action_combo.currentData()
        if action == "playlist":
            self.Load_quality_items(self.playlist_policy_quality_items, ["720p", "Best"])
            self.progress_details_label.setText("The whole playlist will be saved inside its own folder")
            self.downloadButton.setEnabled(len(self.playlist_entries) > 0)
        else:
            if self.selected_playlist_entry:
                entry_quality_items = self.selected_playlist_entry.get("quality_items", [])
                self.Load_quality_items(entry_quality_items, ["720p", "Best"])
                self.downloadButton.setEnabled(self.selected_playlist_entry.get("is_available", False) and len(entry_quality_items) > 0)
            else:
                self.quality_comboBox.clear()
                self.downloadButton.setEnabled(False)
            self.progress_details_label.setText("The selected playlist video will be downloaded")

        self.Update_download_button_text()

    def Handle_playlist_selection(self):
        current_item = self.playlist_preview_list.currentItem()
        if current_item is None:
            self.selected_playlist_entry = None
            self.playlist_selected_value.setText("")
            return

        selected_index = current_item.data(Qt.UserRole)
        if selected_index is None or selected_index < 0 or selected_index >= len(self.playlist_entries):
            self.selected_playlist_entry = None
            self.playlist_selected_value.setText("")
            return

        entry = self.playlist_entries[selected_index]
        self.selected_playlist_entry = entry
        total_entries = len(self.playlist_entries)
        self.playlist_selected_value.setText(f"Selected Video: {entry.get('index', 0):02d}/{total_entries:02d} - {entry.get('title', '-')}")

        if self.playlist_action_combo.currentData() == "selected":
            entry_quality_items = entry.get("quality_items", [])
            self.Load_quality_items(entry_quality_items, ["720p", "Best"])
            self.downloadButton.setEnabled(entry.get("is_available", False) and len(entry_quality_items) > 0)

    def Handle_playlist_action_changed(self):
        self.Refresh_playlist_quality_mode()

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

        url_type = self.Detect_url_type(url)
        self.get_info_btn.setEnabled(False)
        self.downloadButton.setEnabled(False)
        self.status_label.setText("Loading info...")
        self.progress_details_label.setText("Reading media details and available formats")

        self.info_thread = DownloadInfoThread(url, url_type)
        self.info_thread.vidoes_info.connect(self.Handle_video_info)
        self.info_thread.info_failed.connect(self.Handle_info_failed)
        self.info_thread.start()

    def Handle_video_info(self, data):
        self.get_info_btn.setEnabled(True)
        self.Save_url_history(self.Get_url_text())
        self.video_info_loaded = True
        self.info_group.show()

        info_type = data.get("info_type", "video")
        title = data.get("title", "-")
        uploader = data.get("uploader", "Unknown channel")
        thumbnail_data = data.get("thumbnail_data", None)

        self.Set_mode_layout(info_type)
        self.Set_thumbnail_data(thumbnail_data)
        self.info_hint_label.clear()

        if info_type == "playlist":
            self.playlist_title = title
            self.playlist_entries = data.get("entries", [])
            self.playlist_policy_quality_items = data.get("quality_items", [])
            playlist_count = data.get("playlist_count", len(self.playlist_entries))
            total_duration_text = data.get("total_duration_text", "Unknown")

            self.info_type_label.setText("Playlist")
            self.video_title_label.setText(title)
            self.video_duration_label.setText(f"Channel: {uploader}")
            self.playlist_count_value.setText(f"Videos: {playlist_count}")
            self.playlist_total_duration_value.setText(f"Total Duration: {total_duration_text}")
            self.Populate_playlist_entries(self.playlist_entries)
            self.Refresh_playlist_quality_mode()
            self.status_label.setText("Playlist info loaded")
            self.progress_details_label.setText("Choose selected video or full playlist, then start download")
        else:
            duration_text = data.get("duration_text", "-")
            quality_items = data.get("quality_items", [])

            self.info_type_label.setText("Video")
            self.video_title_label.setText(title)
            self.video_duration_label.setText(f"Channel: {uploader}    |    Duration: {duration_text}")
            self.Load_quality_items(quality_items, ["720p", "Best"])
            self.downloadButton.setEnabled(self.quality_comboBox.count() > 0)
            self.status_label.setText("Video info loaded")
            self.progress_details_label.setText("Choose quality and start download")
            self.Update_download_button_text()

    def Handle_info_failed(self, error_text):
        self.get_info_btn.setEnabled(True)
        self.video_info_loaded = False
        self.downloadButton.setEnabled(False)
        self.status_label.setText("Failed to load info")
        self.progress_details_label.setText("Could not read this URL")
        QMessageBox.critical(self, "Error", f"Could not load video info:\n{error_text}")

    def Build_download_request(self):
        url = self.Get_url_text()
        download_type = "video"
        playlist_title = ""

        if self.current_info_type == "playlist":
            action = self.playlist_action_combo.currentData()
            if action == "playlist":
                download_type = "playlist"
                playlist_title = self.playlist_title
            else:
                if self.selected_playlist_entry is None:
                    raise ValueError("Select a playlist video first")

                entry_url = self.selected_playlist_entry.get("webpage_url", "")
                if entry_url == "":
                    raise ValueError("The selected playlist video is not available")

                url = entry_url

        return url, download_type, playlist_title

    def Handle_download(self):
        save_dir = self.Get_save_path_text()
        quality = self.quality_comboBox.currentData()
        if quality is None or quality == "":
            quality = self.quality_comboBox.currentText().strip()

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
            download_url, download_type, playlist_title = self.Build_download_request()
        except ValueError as error:
            QMessageBox.warning(self, "Download Not Ready", str(error))
            return

        self.Save_folder_history()
        self.progressBar.setValue(0)
        self.status_label.setText("Starting download...")

        if download_type == "playlist":
            self.progress_details_label.setText("Preparing full playlist download")
        elif self.current_info_type == "playlist":
            self.progress_details_label.setText("Preparing selected playlist video")
        else:
            self.progress_details_label.setText("Preparing selected video format")

        self.is_downloading = True
        self.downloadButton.setEnabled(False)
        self.Set_download_controls(True)
        self.Set_inputs_enabled(False)

        self.download_thread = DownloadingThread(download_url, save_dir, quality, download_type, playlist_title, self.subtitle_checkBox.isChecked())
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
        self.status_label.setText("Download completed")
        self.progress_details_label.setText("The file was saved successfully")
        self.downloadButton.setEnabled(True)
        self.Set_download_controls(False)
        self.Set_inputs_enabled(True)
        QMessageBox.information(self, "Success", f"Download saved to:\n{save_dir}")

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
