import os
import re
import shutil
from urllib.parse import parse_qs, urlparse

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from app.cache.download_cache_store import DownloadCacheStore
from app.threads.download_thread import DownloadingThread
from app.threads.get_info_thread import DownloadInfoThread
from app.ui.ui_downloader import Ui_MainWindow
from app.ytdlp.core import build_quality_format


class MainApp(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.download_thread = None
        self.info_thread = None
        self.info_request_id = 0
        self.active_info_request_id = 0
        self.loading_info_url = ""
        self.loading_request_id = 0
        self.current_download_cache_rows = []
        self.last_copied_files = []
        self.cache_store = DownloadCacheStore()
        self.cache_store.Load()
        self.video_info_loaded = False
        self.current_info_type = "video"
        self.is_downloading = False
        self.playlist_entries = []
        self.playlist_title = ""
        self.selected_playlist_entry = None
        self.playlist_count = 0
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
        self.CurrentVideo_checkBox.clicked.connect(self.Adv_UI_Setup)
        self.Audio_Only_checkBox.clicked.connect(self.Adv_UI_Setup)
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
        self.Handle_playlist_mode_ui()
        self.Handle_audio_only_mode()
        self.Handle_url_options_mode()

    def Handle_playlist_mode_ui(self):
        range_checked = self.Plst_Range_checkBox.isChecked()
        current_checked = self.CurrentVideo_checkBox.isChecked()

        if range_checked and current_checked:
            if self.sender() == self.CurrentVideo_checkBox:
                self.Plst_Range_checkBox.setChecked(False)
                range_checked = False
            else:
                self.CurrentVideo_checkBox.setChecked(False)
                current_checked = False

        if range_checked:
            self.Plst_Range_frame.show()
            self.CurrentVideo_checkBox.setEnabled(False)
        else:
            self.Plst_Range_frame.hide()
            self.CurrentVideo_checkBox.setEnabled(True)

        if current_checked:
            self.Plst_Range_checkBox.setEnabled(False)
            self.Plst_Range_frame.hide()
        else:
            self.Plst_Range_checkBox.setEnabled(True)

        self.Update_download_button_text()

    def Handle_audio_only_mode(self):
        audio_only_checked = self.Audio_Only_checkBox.isChecked()
        if audio_only_checked:
            self.quality_comboBox.setEnabled(False)
        else:
            self.quality_comboBox.setEnabled(True)

    def Defulat_fun(self):
        self.default = False
        self.Playlist_comboBox.setCurrentIndex(0)

    def Handle_url_options_mode(self):
        url = self.Get_url_text()
        is_playlist_url = self.Is_playlist_context_url(url)

        self.plst_options_groupBox.setEnabled(is_playlist_url)

        if not is_playlist_url:
            self.Plst_Range_checkBox.setChecked(False)
            self.CurrentVideo_checkBox.setChecked(False)
            self.Plst_Range_frame.hide()
            self.Plst_Range_checkBox.setEnabled(False)
            self.CurrentVideo_checkBox.setEnabled(False)
            self.Playlist_comboBox.setEnabled(False)
            self.playlist_num_display.hide()
        else:
            self.Plst_Range_checkBox.setEnabled(True)
            self.CurrentVideo_checkBox.setEnabled(True)
            self.Playlist_comboBox.setEnabled(True)
            self.Handle_playlist_mode_ui()

        self.Update_download_button_text()

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
            self.Handle_playlist_mode_ui()

        elif checkbox == self.CurrentVideo_checkBox:
            self.Handle_playlist_mode_ui()

        elif checkbox == self.Audio_Only_checkBox:
            self.Handle_audio_only_mode()

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
        if enabled:
            self.Handle_audio_only_mode()

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
        parsed_info = self.Handle_parse_youtube_url(url)
        if not parsed_info["is_youtube"]:
            return "video"

        has_list = parsed_info["has_list"]
        has_video = parsed_info["has_video"]
        path_type = parsed_info["path_type"]

        if has_list and has_video:
            return "mixed"

        if path_type == "playlist" and has_list:
            return "playlist"

        if has_list and not has_video:
            return "playlist"

        return "video"

    def Is_youtube_url(self, url):
        parsed_info = self.Handle_parse_youtube_url(url)
        return parsed_info["is_youtube"]

    def Handle_normalize_url(self, url):
        url_text = str(url or "").strip()
        if url_text == "":
            return ""
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url_text):
            return f"https://{url_text}"
        return url_text

    def Handle_parse_youtube_url(self, url):
        url_text = self.Handle_normalize_url(url)
        if url_text == "":
            return {
                "is_youtube": False,
                "has_list": False,
                "has_video": False,
                "path_type": "unknown",
                "query": {},
            }

        try:
            parsed = urlparse(url_text)
        except Exception:
            return {
                "is_youtube": False,
                "has_list": False,
                "has_video": False,
                "path_type": "unknown",
                "query": {},
            }

        host = str(parsed.netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]

        allowed_hosts = {
            "youtube.com",
            "m.youtube.com",
            "music.youtube.com",
            "youtu.be",
            "youtube-nocookie.com",
        }
        is_youtube = host in allowed_hosts

        query = parse_qs(parsed.query)
        list_values = query.get("list", [])
        video_values = query.get("v", [])

        has_list = any(str(value).strip() != "" for value in list_values)
        has_video = any(str(value).strip() != "" for value in video_values)

        path_value = str(parsed.path or "").lower()
        path_type = "unknown"
        if path_value.startswith("/playlist"):
            path_type = "playlist"
        elif path_value.startswith("/watch"):
            path_type = "watch"
        elif path_value.startswith("/live/"):
            path_type = "live"
        elif host == "youtu.be" and path_value.strip("/") != "":
            path_type = "short_watch"
            has_video = True

        if path_type in {"watch", "live", "short_watch"} and not has_video:
            has_video = True

        return {
            "is_youtube": is_youtube,
            "has_list": has_list,
            "has_video": has_video,
            "path_type": path_type,
            "query": query,
            "path_value": path_value,
        }

    def Handle_video_id_from_url(self, url):
        parsed_info = self.Handle_parse_youtube_url(url)
        query = parsed_info.get("query", {})
        v_values = query.get("v", [])
        if len(v_values) > 0:
            video_id = str(v_values[0]).strip()
            if video_id != "":
                return video_id

        if parsed_info.get("path_type") == "short_watch":
            path_value = str(parsed_info.get("path_value", ""))
            return path_value.strip("/").strip()

        return ""

    def Handle_list_id_from_url(self, url):
        parsed_info = self.Handle_parse_youtube_url(url)
        query = parsed_info.get("query", {})
        list_values = query.get("list", [])
        if len(list_values) > 0:
            list_id = str(list_values[0]).strip()
            if list_id != "":
                return list_id
        return ""

    def Handle_simple_format_text(self, quality):
        quality_text = str(quality or "").strip()
        if quality_text == "":
            return "unknown"

        match = re.search(r"\b(\d{2,4})\b", quality_text)
        if match:
            return match.group(1)

        lower_text = quality_text.lower()
        if "audio" in lower_text:
            return "audio"
        if "best" in lower_text:
            return "best"
        return "custom"

    def Handle_video_id_from_entry(self, entry):
        webpage_url = str(entry.get("webpage_url", "")).strip()
        if webpage_url != "":
            video_id = self.Handle_video_id_from_url(webpage_url)
            if video_id != "":
                return video_id
        return ""

    def Handle_selected_playlist_indexes(self, playlist_items, total_count):
        if str(playlist_items).strip() == "":
            return list(range(1, max(0, int(total_count)) + 1))

        selected_numbers = set()
        text_items = [part.strip() for part in str(playlist_items).split(",") if part.strip() != ""]
        for text_item in text_items:
            if text_item.isdigit():
                selected_numbers.add(int(text_item))
                continue
            if "-" in text_item:
                left_right = text_item.split("-", 1)
                if len(left_right) != 2:
                    continue
                left_text = left_right[0].strip()
                right_text = left_right[1].strip()
                if (not left_text.isdigit()) or (not right_text.isdigit()):
                    continue
                left = int(left_text)
                right = int(right_text)
                if right < left:
                    left, right = right, left
                for value in range(left, right + 1):
                    selected_numbers.add(value)

        filtered = [value for value in sorted(selected_numbers) if 1 <= value <= int(total_count)]
        return filtered

    def Build_download_cache_rows(self, download_url, download_type, quality, playlist_items):
        rows = []
        format_raw = str(quality or "")
        format_simple = self.Handle_simple_format_text(quality)
        list_id = self.Handle_list_id_from_url(download_url)
        target_dir = self.Get_save_path_text()

        if download_type == "playlist":
            total_count = len(self.playlist_entries)
            selected_indexes = self.Handle_selected_playlist_indexes(playlist_items, total_count)
            if len(selected_indexes) == 0:
                selected_indexes = list(range(1, total_count + 1))

            for index_value in selected_indexes:
                if index_value < 1 or index_value > len(self.playlist_entries):
                    continue
                entry = self.playlist_entries[index_value - 1]
                video_id = self.Handle_video_id_from_entry(entry)
                rows.append(
                    {
                        "video_id": video_id,
                        "list_id": list_id,
                        "download_type": "playlist",
                        "playlist_item": str(index_value),
                        "playlist_items": str(playlist_items or ""),
                        "format_simple": format_simple,
                        "format_raw": format_raw,
                        "target_dir": target_dir,
                    }
                )
            return rows

        video_id = self.Handle_video_id_from_url(download_url)
        rows.append(
            {
                "video_id": video_id,
                "list_id": list_id,
                "download_type": "video",
                "playlist_item": "",
                "playlist_items": "",
                "format_simple": format_simple,
                "format_raw": format_raw,
                "target_dir": target_dir,
            }
        )
        return rows

    def Is_playlist_context_url(self, url):
        parsed_info = self.Handle_parse_youtube_url(url)
        return parsed_info["is_youtube"] and parsed_info["has_list"]

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
            if self.CurrentVideo_checkBox.isChecked():
                self.downloadButton.setText("Download Current")
                return
            if self.Plst_Range_checkBox.isChecked():
                self.downloadButton.setText("Download Range")
                return
            self.downloadButton.setText("Download Playlist")
            return
        self.downloadButton.setText("Download Video")

    def Set_empty_info_state(self):
        self.playlist_entries = []
        self.playlist_title = ""
        self.selected_playlist_entry = None
        self.playlist_count = 0
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
        self.Handle_audio_only_mode()
        self.Update_download_button_text()

    def Reset_video_info(self):
        if self.is_downloading:
            return
        self.Set_empty_info_state()

    def Handle_url_text_changed(self, _text=""):
        self.Cancel_info_thread()
        self.Reset_video_info()
        self.Handle_url_options_mode()
        self.Schedule_auto_get_video_info()

    def Cancel_info_thread(self):
        if self.info_thread is None:
            return

        try:
            self.info_thread.Handle_stop_request()
        except Exception:
            pass

        self.info_request_id += 1
        self.active_info_request_id = self.info_request_id
        self.loading_info_url = ""
        self.loading_request_id = 0

    def Next_info_request_id(self):
        self.info_request_id += 1
        self.active_info_request_id = self.info_request_id
        return self.active_info_request_id

    def Schedule_auto_get_video_info(self):
        if self.is_downloading:
            return

        url = self.Get_url_text()
        if not self.Is_youtube_url(url):
            self.auto_info_timer.stop()
            return

        if url == self.last_loaded_url and self.video_info_loaded:
            return

        normalized_url = self.Handle_normalize_url(url)
        if normalized_url != "" and self.loading_info_url == normalized_url:
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

    def Is_info_request_ready(self, url):
        normalized_url = self.Handle_normalize_url(url)
        if normalized_url == "":
            return False

        if self.loading_info_url == normalized_url:
            return False

        return True

    def Populate_playlist_comboBox(self):
        self.Playlist_comboBox.blockSignals(True)
        self.Playlist_comboBox.clear()
        for entry in self.playlist_entries:
            index_value = int(entry.get("index", 0))
            entry_title = str(entry.get("title", "")).strip()
            if entry_title == "":
                entry_title = f"Video {index_value}"
            short_title = entry_title
            if len(short_title) > 45:
                short_title = short_title[:42].rstrip() + "..."
            item_text = f"{index_value}. {short_title}"
            self.Playlist_comboBox.addItem(item_text, index_value)
            item_row = self.Playlist_comboBox.count() - 1
            self.Playlist_comboBox.setItemData(item_row, entry_title, Qt.ToolTipRole)
        if self.Playlist_comboBox.count() > 0:
            self.Playlist_comboBox.setCurrentIndex(0)
            self.Playlist_comboBox.view().setMinimumWidth(520)
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

    def Handle_Playlist_items_range(self):
        total_count = max(0, int(self.playlist_count or len(self.playlist_entries)))
        if total_count <= 0:
            return "", 0

        if self.CurrentVideo_checkBox.isChecked() and self.selected_playlist_entry is not None:
            index_value = int(self.selected_playlist_entry.get("index", 0))
            if 1 <= index_value <= total_count:
                return str(index_value), 1

        if not self.Plst_Range_checkBox.isChecked():
            return "", total_count

        start = self.Range_start_spnbx.value()
        end = self.Range_end_spnbx.value()
        if end < start:
            start, end = end, start

        start = max(1, min(total_count, int(start)))
        end = max(1, min(total_count, int(end)))

        items_ranges = [f"{start}-{end}"]
        items_nums = []
        items_count = self.Items_Range_cmbx.count()

        for i in range(items_count):
            item = self.Items_Range_cmbx.itemText(i).strip().replace(" ", "")
            if item == "":
                continue
            if item.isdigit():
                value = int(item)
                if 1 <= value <= total_count:
                    items_nums.append(str(value))
            elif "-" in item:
                parts = item.split("-")
                if (len(parts) == 2) and (parts[0].isdigit()) and (parts[1].isdigit()):
                    left = int(parts[0])
                    right = int(parts[1])
                    if right < left:
                        left, right = right, left
                    left = max(1, min(total_count, left))
                    right = max(1, min(total_count, right))
                    if right >= left:
                        items_ranges.append(f"{left}-{right}")

        current_item = self.Items_Range_cmbx.currentText().strip().replace(" ", "")
        if current_item != "":
            if current_item.isdigit():
                value = int(current_item)
                if 1 <= value <= total_count:
                    items_nums.append(str(value))
            elif "-" in current_item:
                parts = current_item.split("-")
                if (len(parts) == 2) and (parts[0].isdigit()) and (parts[1].isdigit()):
                    left = int(parts[0])
                    right = int(parts[1])
                    if right < left:
                        left, right = right, left
                    left = max(1, min(total_count, left))
                    right = max(1, min(total_count, right))
                    if right >= left:
                        items_ranges.append(f"{left}-{right}")

        all_items = items_nums + items_ranges
        unique_items = []
        seen_items = set()
        selected_numbers = set()
        for item in all_items:
            if item not in seen_items:
                unique_items.append(item)
                seen_items.add(item)
            if "-" in item:
                left, right = item.split("-", 1)
                for number_value in range(int(left), int(right) + 1):
                    selected_numbers.add(number_value)
            elif item.isdigit():
                selected_numbers.add(int(item))

        if len(unique_items) == 0:
            return "", total_count

        return ",".join(unique_items), len(selected_numbers)

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

        if not self.Is_info_request_ready(url):
            return

        self.Cancel_info_thread()

        url_type = self.Detect_url_type(url)
        effective_url_type = "video" if url_type == "mixed" else url_type
        request_id = self.Next_info_request_id()
        self.get_info_btn.setEnabled(False)
        self.downloadButton.setEnabled(False)
        self.status_label.setText("Loading info...")
        if url_type == "mixed":
            self.progress_details_label.setText("Detected video inside playlist. Loading as video by default")
        else:
            self.progress_details_label.setText("Reading media details and available formats")

        normalized_url = self.Handle_normalize_url(url)
        self.loading_info_url = normalized_url
        self.loading_request_id = request_id
        self.info_thread = DownloadInfoThread(url, effective_url_type, request_id, self.Thumbnail_checkBox.isChecked())
        self.info_thread.vidoes_info.connect(self.Handle_video_info)
        self.info_thread.update_Entreis.connect(self.Handle_playlist_entry_update)
        self.info_thread.info_failed.connect(self.Handle_info_failed)
        self.info_thread.start()

    def Handle_playlist_entry_update(self, request_id, entry_update):
        if int(request_id) != int(self.active_info_request_id):
            return

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
            combo_text = updated_title
            if len(combo_text) > 45:
                combo_text = combo_text[:42].rstrip() + "..."
            item_label = f"{entry_index + 1}. {combo_text}"
            self.Playlist_comboBox.setItemText(entry_index, item_label)
            self.Playlist_comboBox.setItemData(entry_index, updated_title, Qt.ToolTipRole)

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

    def Handle_video_info(self, request_id, data):
        if int(request_id) != int(self.active_info_request_id):
            return

        self.info_thread = None
        self.loading_info_url = ""
        self.loading_request_id = 0
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
            self.playlist_count = int(playlist_count)

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

    def Handle_info_failed(self, request_id, error_text):
        if int(request_id) != int(self.active_info_request_id):
            return

        self.info_thread = None
        self.loading_info_url = ""
        self.loading_request_id = 0
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
        playlist_count_for_prefix = 0
        playlist_items = ""
        quality = self.quality_comboBox.currentData()
        if quality is None or quality == "":
            quality = self.quality_comboBox.currentText().strip()

        if self.Audio_Only_checkBox.isChecked():
            quality = "Audio only (139)"

        if self.current_info_type == "playlist":
            if self.selected_playlist_entry is None:
                raise ValueError("Select playlist video index first")
            download_type = "playlist"
            playlist_title = self.playlist_title
            total_playlist_count = max(0, int(self.playlist_count or len(self.playlist_entries)))
            playlist_items, selected_count = self.Handle_Playlist_items_range()
            playlist_count_for_prefix = total_playlist_count
            if self.prefix_no_cmbx.currentIndex() == 1 and selected_count > 0:
                playlist_count_for_prefix = selected_count
            if not self.Audio_Only_checkBox.isChecked():
                quality = self.Build_playlist_quality_from_selection()

        return url, download_type, playlist_title, quality, playlist_count_for_prefix, playlist_items

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
            download_url, download_type, playlist_title, quality, playlist_count_for_prefix, playlist_items = self.Build_download_request()
        except ValueError as error:
            QMessageBox.warning(self, "Download Not Ready", str(error))
            return

        cache_rows = self.Build_download_cache_rows(download_url, download_type, quality, playlist_items)
        reused = self.Handle_reuse_done_file(cache_rows, save_dir)
        if reused:
            self.current_download_cache_rows = cache_rows
            self.Download_finished(save_dir)
            return

        self.Save_folder_history()
        self.progressBar.setValue(0)
        self.status_label.setText("Starting download...")

        if download_type == "playlist":
            if playlist_items != "":
                self.progress_details_label.setText(f"Preparing playlist range download: {playlist_items}")
            else:
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
            playlist_count_for_prefix if download_type == "playlist" else 0,
            playlist_items if download_type == "playlist" else "",
            self.Add_Prefix_checkBox.isChecked() if download_type == "playlist" else False,
            self.prefix_no_cmbx.currentIndex() if download_type == "playlist" else 0,
            self.Add_Suffix_checkBox.isChecked(),
            self.Suffix_lineEdit.text(),
            self.subtitle_checkBox.isChecked(),
            self.chapters_checkBox.isChecked(),
            self.current_video_language,
        )

        self.current_download_cache_rows = cache_rows
        self.last_copied_files = []
        for cache_row in self.current_download_cache_rows:
            self.cache_store.Upsert_download_state(
                cache_row.get("video_id", ""),
                cache_row.get("list_id", ""),
                cache_row.get("download_type", ""),
                cache_row.get("playlist_item", ""),
                cache_row.get("playlist_items", ""),
                cache_row.get("format_simple", ""),
                cache_row.get("format_raw", ""),
                "queued",
                temp_dir="",
                temp_file="",
                target_dir=cache_row.get("target_dir", save_dir),
                target_name="",
                auto_save=True,
            )
        self.download_thread.progress_changed.connect(self.Update_progress)
        self.download_thread.status_changed.connect(self.Update_status)
        self.download_thread.details_changed.connect(self.Update_progress_details)
        self.download_thread.download_finished.connect(self.Download_finished)
        self.download_thread.download_failed.connect(self.Download_failed)
        self.download_thread.download_cancelled.connect(self.Download_cancelled)
        self.download_thread.files_copied.connect(self.Handle_download_files_copied)
        self.download_thread.start()

        for cache_row in self.current_download_cache_rows:
            self.cache_store.Upsert_download_state(
                cache_row.get("video_id", ""),
                cache_row.get("list_id", ""),
                cache_row.get("download_type", ""),
                cache_row.get("playlist_item", ""),
                cache_row.get("playlist_items", ""),
                cache_row.get("format_simple", ""),
                cache_row.get("format_raw", ""),
                "downloading",
                temp_dir="",
                temp_file="",
                target_dir=cache_row.get("target_dir", save_dir),
                target_name="",
                auto_save=True,
            )

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

    def Handle_download_files_copied(self, files_list):
        if isinstance(files_list, list):
            self.last_copied_files = [str(x) for x in files_list if str(x).strip() != ""]
        else:
            self.last_copied_files = []

    def Handle_reuse_done_file(self, cache_rows, save_dir):
        if len(cache_rows) != 1:
            return False

        cache_row = cache_rows[0]
        cache_key = self.cache_store.Build_cache_key(
            cache_row.get("video_id", ""),
            cache_row.get("list_id", ""),
            cache_row.get("download_type", ""),
            cache_row.get("playlist_item", ""),
            cache_row.get("format_simple", ""),
        )
        if cache_key == "":
            return False

        old_row = self.cache_store.rows_by_key.get(cache_key, {})
        if str(old_row.get("state", "")).lower() != "done":
            return False

        old_target_dir = str(old_row.get("target_dir", "")).strip()
        old_target_name = str(old_row.get("target_name", "")).strip()
        if old_target_dir == "" or old_target_name == "":
            return False

        source_file = os.path.join(old_target_dir, old_target_name)
        if not os.path.isfile(source_file):
            return False

        os.makedirs(save_dir, exist_ok=True)
        target_file = os.path.join(save_dir, old_target_name)
        if os.path.normcase(source_file) == os.path.normcase(target_file):
            return True

        if not os.path.isfile(target_file):
            try:
                shutil.copy2(source_file, target_file)
            except Exception:
                return False

        self.last_copied_files = [old_target_name]
        return True

    def Download_finished(self, save_dir):
        target_name_text = ""
        if len(self.last_copied_files) == 1:
            target_name_text = os.path.basename(self.last_copied_files[0])

        for cache_row in self.current_download_cache_rows:
            self.cache_store.Upsert_download_state(
                cache_row.get("video_id", ""),
                cache_row.get("list_id", ""),
                cache_row.get("download_type", ""),
                cache_row.get("playlist_item", ""),
                cache_row.get("playlist_items", ""),
                cache_row.get("format_simple", ""),
                cache_row.get("format_raw", ""),
                "done",
                temp_dir="",
                temp_file="",
                target_dir=save_dir,
                target_name=target_name_text,
                auto_save=True,
            )
        self.Save_url_history(self.Get_url_text())
        self.is_downloading = False
        self.download_thread = None
        self.current_download_cache_rows = []
        self.last_copied_files = []
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
        for cache_row in self.current_download_cache_rows:
            self.cache_store.Upsert_download_state(
                cache_row.get("video_id", ""),
                cache_row.get("list_id", ""),
                cache_row.get("download_type", ""),
                cache_row.get("playlist_item", ""),
                cache_row.get("playlist_items", ""),
                cache_row.get("format_simple", ""),
                cache_row.get("format_raw", ""),
                "failed",
                last_error=str(error_text or ""),
                auto_save=True,
            )
        self.is_downloading = False
        self.download_thread = None
        self.current_download_cache_rows = []
        self.last_copied_files = []
        self.status_label.setText("Download failed")
        self.progress_details_label.setText("The download stopped before the file could be saved")
        self.downloadButton.setEnabled(True)
        self.Set_download_controls(False)
        self.Set_inputs_enabled(True)
        QMessageBox.critical(self, "Error", f"Download failed:\n{error_text}")

    def Download_cancelled(self):
        for cache_row in self.current_download_cache_rows:
            self.cache_store.Upsert_download_state(
                cache_row.get("video_id", ""),
                cache_row.get("list_id", ""),
                cache_row.get("download_type", ""),
                cache_row.get("playlist_item", ""),
                cache_row.get("playlist_items", ""),
                cache_row.get("format_simple", ""),
                cache_row.get("format_raw", ""),
                "partial",
                auto_save=True,
            )
        self.is_downloading = False
        self.download_thread = None
        self.current_download_cache_rows = []
        self.last_copied_files = []
        self.status_label.setText("Download cancelled")
        self.progressBar.setValue(0)
        self.progress_details_label.setText("The active download was cancelled")
        self.downloadButton.setEnabled(True)
        self.Set_download_controls(False)
        self.Set_inputs_enabled(True)

    def closeEvent(self, event):
        self.cache_store.Save()
        super().closeEvent(event)
