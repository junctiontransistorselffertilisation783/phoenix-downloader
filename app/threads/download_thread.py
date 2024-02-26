import os
import re
import threading

import yt_dlp
from yt_dlp.utils import DownloadCancelled
from PyQt5.QtCore import QThread, pyqtSignal
from app.utils.helpers import handle_num, format_bytes, format_seconds, safe_name
from app.ytdlp.core import (
    build_download_options,
    build_subtitle_download_options,
    build_subtitle_passes,
    is_subtitle_error,
)

class DownloadingThread(QThread):
    progress_changed = pyqtSignal(int)
    status_changed = pyqtSignal(str)
    details_changed = pyqtSignal(str)
    download_finished = pyqtSignal(str)
    download_failed = pyqtSignal(str)
    download_cancelled = pyqtSignal()

    def __init__(
        self,
        url,
        save_dir,
        quality,
        download_type="video",
        playlist_title="",
        playlist_count=0,
        playlist_selected_count=0,
        playlist_items="",
        add_prefix=False,
        prefix_mode=0,
        add_suffix=False,
        suffix_text="",
        download_subtitles=False,
        download_chapters=False,
        video_language="",
    ):
        super().__init__()
        self.url = url
        self.save_dir = save_dir
        self.quality = quality
        self.download_type = download_type
        self.playlist_title = playlist_title
        self.playlist_count = int(playlist_count or 0)
        self.playlist_selected_count = int(playlist_selected_count or 0)
        self.playlist_items = str(playlist_items or "").strip()
        self.add_prefix = bool(add_prefix)
        self.prefix_mode = int(prefix_mode or 0)
        self.add_suffix = bool(add_suffix)
        self.suffix_text = str(suffix_text or "")
        self.download_subtitles = download_subtitles
        self.download_chapters = download_chapters
        self.video_language = video_language
        self.stop_requested = False
        self.chapter_targets = {}
        self.subtitle_thread = None
        self.subtitle_errors = []
        self.subtitle_fatal_error = None
        self.chapter_thread = None
        self.output_template = ""
        self.media_progress_state = {}
        self.last_global_progress = 0

    def Build_playlist_prefix_template(self):
        if not self.add_prefix:
            return ""

        count_for_digits = self.playlist_count
        if self.prefix_mode == 1 and self.playlist_selected_count > 0:
            count_for_digits = self.playlist_selected_count

        if count_for_digits >= 100:
            digits = 3
        elif count_for_digits >= 10:
            digits = 2
        else:
            digits = 1

        if self.prefix_mode == 1:
            field_name = "playlist_autonumber"
        else:
            field_name = "playlist_index"

        return f"%({field_name})0{digits}d - "

    def Is_subtitle_file(self, info_dict):
        ext_value = str(info_dict.get("ext", "")).lower()
        return ext_value in ["vtt", "srt", "ttml", "sbv", "json"]

    def Handle_suffix_text(self):
        if not self.add_suffix:
            return ""

        suffix = self.suffix_text.strip()
        if suffix == "":
            return ""

        suffix = re.sub(r"[\\/:*?\"<>|]", "-", suffix)
        suffix = re.sub(r"\s+", " ", suffix).strip()
        if suffix == "":
            return ""

        if not suffix.startswith(" "):
            suffix = f" {suffix}"

        return suffix

    def Cancel_download(self):
        self.stop_requested = True

    def Handle_stream_size(self, format_info, duration_seconds):
        if not isinstance(format_info, dict):
            return 0

        size_value = format_info.get("filesize")
        if size_value:
            return handle_num(size_value)

        size_value = format_info.get("filesize_approx")
        if size_value:
            return handle_num(size_value)

        tbr_value = format_info.get("tbr")
        if tbr_value and duration_seconds:
            return handle_num((float(tbr_value) * 1000 / 8) * float(duration_seconds))

        return 0

    def Handle_item_key(self, info_dict):
        video_id = str(info_dict.get("id", "")).strip()
        if video_id != "":
            return video_id

        title_text = str(info_dict.get("title", "")).strip()
        if title_text != "":
            return f"title::{title_text}"

        return "default-item"

    def Ensure_item_state(self, info_dict):
        item_key = self.Handle_item_key(info_dict)
        if item_key in self.media_progress_state:
            return item_key, self.media_progress_state[item_key]

        duration_seconds = handle_num(info_dict.get("duration"))
        expected_total = 0
        requested_formats = info_dict.get("requested_formats", [])
        if isinstance(requested_formats, list) and len(requested_formats) > 0:
            for stream_info in requested_formats:
                expected_total += self.Handle_stream_size(stream_info, duration_seconds)
        else:
            expected_total = self.Handle_stream_size(info_dict, duration_seconds)

        self.media_progress_state[item_key] = {
            "expected_total": expected_total,
            "runtime_total": 0,
            "stream_totals": {},
            "stream_downloaded": {},
            "last_percent": 0,
        }
        return item_key, self.media_progress_state[item_key]

    def Handle_stream_key(self, info_dict):
        format_id = str(info_dict.get("format_id", "")).strip()
        if format_id != "":
            return format_id

        ext_value = str(info_dict.get("ext", "")).strip()
        if ext_value != "":
            return ext_value

        return "main-stream"

    def Compute_combined_progress(self, item_state, stream_key, downloaded_now, total_bytes, total_estimate):
        runtime_stream_total = 0
        if total_bytes is not None:
            runtime_stream_total = handle_num(total_bytes)
        elif total_estimate is not None:
            runtime_stream_total = handle_num(total_estimate)

        stream_downloaded = item_state["stream_downloaded"]
        stream_downloaded[stream_key] = max(downloaded_now, stream_downloaded.get(stream_key, 0))

        stream_totals = item_state["stream_totals"]
        if runtime_stream_total > 0:
            stream_totals[stream_key] = max(runtime_stream_total, stream_totals.get(stream_key, 0))

        if runtime_stream_total > 0:
            item_state["runtime_total"] = max(item_state["runtime_total"], runtime_stream_total)

        downloaded_total = sum(handle_num(stream_value) for stream_value in stream_downloaded.values())
        streams_total_sum = sum(handle_num(total_value) for total_value in stream_totals.values())

        known_total = max(item_state["expected_total"], item_state["runtime_total"], streams_total_sum)
        if known_total > 0:
            percent_value = int((downloaded_total / known_total) * 100)
            if percent_value > 99:
                percent_value = 99
            if percent_value < item_state["last_percent"]:
                percent_value = item_state["last_percent"]
            item_state["last_percent"] = percent_value
            return percent_value, downloaded_total, known_total

        fallback_percent = item_state["last_percent"]
        if runtime_stream_total > 0 and downloaded_now > 0:
            fallback_percent = int((downloaded_now / runtime_stream_total) * 100)
            if fallback_percent > 99:
                fallback_percent = 99
            if fallback_percent < item_state["last_percent"]:
                fallback_percent = item_state["last_percent"]
            item_state["last_percent"] = fallback_percent

        return fallback_percent, downloaded_total, known_total

    def Handle_ydl_opts(self, output_template):
        return build_download_options(
            output_template=output_template,
            quality=self.quality,
            download_type=self.download_type,
            progress_hook=self.progress_hook,
            playlist_items=self.playlist_items,
        )

    def Handle_subtitle_pass_options(self, output_template, subtitle_options):
        return build_subtitle_download_options(
            output_template=output_template,
            progress_hook=self.progress_hook,
            subtitle_options=subtitle_options,
            download_type=self.download_type,
            playlist_items=self.playlist_items,
        )

    def progress_hook(self, d):
        if self.stop_requested:
            raise DownloadCancelled("Download cancelled by user")

        status = ""
        total_size = 0
        downloaded = 0
        speed_value = None
        eta_value = None
        
        if "status" in d:
            status = d.get("status", "")

        if status == "downloading":
            downloaded = handle_num(d.get("downloaded_bytes", 0))
            info_dict = d.get("info_dict", {})
            is_subtitle_file = self.Is_subtitle_file(info_dict)

            if not is_subtitle_file:
                self.Start_subtitles_background()

            total_bytes = d.get("total_bytes")
            total_estimate = d.get("total_bytes_estimate")
            if total_bytes is not None:
                total_size = handle_num(total_bytes)
            elif total_estimate is not None:
                total_size = handle_num(total_estimate)

            if not is_subtitle_file:
                stream_key = self.Handle_stream_key(info_dict)
                _item_key, item_state = self.Ensure_item_state(info_dict)
                percent_value, downloaded_combined, total_combined = self.Compute_combined_progress(
                    item_state,
                    stream_key,
                    downloaded,
                    total_bytes,
                    total_estimate,
                )

                progress_value = max(self.last_global_progress, percent_value)
                self.last_global_progress = progress_value
                self.progress_changed.emit(progress_value)
                downloaded = downloaded_combined
                total_size = total_combined

            speed_value = handle_num(d.get("speed"))
            eta_value = handle_num(d.get("eta"))

            percent_value = 0
            if is_subtitle_file:
                if total_size > 0:
                    percent_value = int((downloaded / total_size) * 100)
            else:
                percent_value = self.last_global_progress

            downloaded_text = format_bytes(downloaded)
            total_text = format_bytes(total_size)
            speed_text = format_bytes(speed_value)
            eta_text = format_seconds(eta_value)

            detail_parts = []
            if total_text and downloaded_text:
                detail_parts.append(f"{downloaded_text} of {total_text}")
            elif downloaded_text:
                detail_parts.append(downloaded_text)

            if speed_text:
                detail_parts.append(f"{speed_text}/s")

            if eta_text:
                detail_parts.append(f"ETA {eta_text}")

            status_prefix = "Downloading"
            if self.download_type == "playlist":
                playlist_index = info_dict.get("playlist_index")
                playlist_count = info_dict.get("n_entries") or info_dict.get("playlist_count")
                if playlist_index and playlist_count:
                    status_prefix = f"Item {playlist_index} of {playlist_count}"

            title_text = str(info_dict.get("title", "")).strip()
            if title_text:
                detail_parts.insert(0, title_text)

            if is_subtitle_file:
                detail_parts.insert(0, "Subtitle file")

            if not is_subtitle_file:
                self.status_changed.emit(f"{status_prefix}  {percent_value}%")
            self.details_changed.emit("   |   ".join(detail_parts) if detail_parts else "Receiving video data")

        if status == "finished":
            info_dict = d.get("info_dict", {})
            is_subtitle_file = self.Is_subtitle_file(info_dict)
            if self.download_chapters and not is_subtitle_file:
                chapters = info_dict.get("chapters")
                output_filename = d.get("filename")
                if output_filename and isinstance(chapters, list) and len(chapters) > 0:
                    self.chapter_targets[output_filename] = chapters

            if not is_subtitle_file:
                if self.last_global_progress < 99:
                    self.last_global_progress = 99
                self.progress_changed.emit(self.last_global_progress)
                self.status_changed.emit("Finalizing file")
                self.details_changed.emit("Merging audio and video, then saving the final file")

    def Write_chapters_files(self):
        if not self.chapter_targets:
            return

        written_count = 0
        written_paths = set()
        for output_filename, chapters in self.chapter_targets.items():
            base_name, _ = os.path.splitext(output_filename)
            base_name = re.sub(r"\.f\d+$", "", base_name)
            chapter_file_path = f"{base_name}.pbf"
            if chapter_file_path in written_paths:
                continue

            try:
                with open(chapter_file_path, "w", encoding="utf-8") as chapter_file:
                    chapter_file.write("[Bookmark]\n")
                    for index, chapter in enumerate(chapters):
                        end_time = chapter.get("end_time")
                        title = str(chapter.get("title", f"Chapter {index + 1}")).replace("*", "-")
                        if end_time is None:
                            continue
                        chapter_file.write(f"{index}={int(float(end_time) * 1000)}*{title}*\n")
                written_count += 1
                written_paths.add(chapter_file_path)
            except Exception:
                continue

        if written_count > 0:
            self.status_changed.emit("Chapters files created")
            self.details_changed.emit(f"Created {written_count} PotPlayer chapter file(s)")

    def Cleanup_subtitle_orig_files(self, output_template):
        template_dir = os.path.dirname(output_template)
        if not os.path.isdir(template_dir):
            return

        try:
            for name in os.listdir(template_dir):
                file_name_lower = name.lower()
                if file_name_lower.endswith("-orig.srt") or file_name_lower.endswith("-orig.vtt"):
                    try:
                        os.remove(os.path.join(template_dir, name))
                    except Exception:
                        continue
        except Exception:
            return

    def Run_subtitles_background(self, output_template):
        if (not self.download_subtitles) or self.stop_requested:
            return

        self.subtitle_errors = []
        self.subtitle_fatal_error = None

        subtitle_passes = build_subtitle_passes(self.download_subtitles, self.video_language)
        for subtitle_pass in subtitle_passes:
            if self.stop_requested:
                return

            pass_name = subtitle_pass.get("name", "subtitles")
            subtitle_pass_options = subtitle_pass.get("options", {})
            if not subtitle_pass_options:
                continue

            self.status_changed.emit(f"Trying {pass_name}")
            self.details_changed.emit("Subtitle step is optional and will not stop video")

            subtitle_options = self.Handle_subtitle_pass_options(output_template, subtitle_pass_options)
            try:
                with yt_dlp.YoutubeDL(subtitle_options) as ydl: # pyright: ignore[reportArgumentType]
                    ydl.download([self.url])
            except DownloadCancelled:
                return
            except Exception as error:
                error_text = str(error)
                if is_subtitle_error(error_text):
                    self.subtitle_errors.append(error_text)
                    continue
                self.subtitle_fatal_error = error
                return

        self.Cleanup_subtitle_orig_files(output_template)

    def Start_subtitles_background(self):
        if self.stop_requested:
            return
        if not self.download_subtitles:
            return
        if self.subtitle_thread is not None:
            return
        if self.output_template == "":
            return

        self.subtitle_thread = threading.Thread(
            target=self.Run_subtitles_background,
            args=(self.output_template,),
            daemon=True,
        )
        self.subtitle_thread.start()

    def Run_chapters_background(self):
        try:
            self.Write_chapters_files()
        except Exception:
            return

    def run(self):
        try:
            self.status_changed.emit("Preparing download")
            self.details_changed.emit("Connecting to YouTube and preparing the selected format")

            output_template = os.path.join(self.save_dir, "%(title)s.%(ext)s")
            suffix_text = self.Handle_suffix_text()
            if self.download_type == "playlist":
                folder_title = safe_name(self.playlist_title)
                if self.playlist_count > 0:
                    folder_title = f"{folder_title} [ {self.playlist_count} ]"
                playlist_folder = os.path.join(self.save_dir, folder_title)
                os.makedirs(playlist_folder, exist_ok=True)
                prefix_template = self.Build_playlist_prefix_template()
                output_template = os.path.join(playlist_folder, f"{prefix_template}%(title)s{suffix_text}.%(ext)s")
            else:
                output_template = os.path.join(self.save_dir, f"%(title)s{suffix_text}.%(ext)s")
            self.output_template = output_template

            ydl_opts = self.Handle_ydl_opts(output_template)

            with yt_dlp.YoutubeDL(ydl_opts) as ydl: # pyright: ignore[reportArgumentType]
                ydl.download([self.url])

            if self.download_chapters and not self.stop_requested:
                self.chapter_thread = threading.Thread(
                    target=self.Run_chapters_background,
                    daemon=True,
                )
                self.chapter_thread.start()

            if self.subtitle_thread is not None or self.chapter_thread is not None:
                self.status_changed.emit("Media saved")
                self.details_changed.emit("Subtitle/chapter tasks may continue in background")

            if self.stop_requested:
                self.download_cancelled.emit()
                return

            self.last_global_progress = 100
            self.progress_changed.emit(100)
            self.download_finished.emit(self.save_dir)

        except Exception as error:
            if self.stop_requested:
                self.download_cancelled.emit()
                return

            self.download_failed.emit(str(error))
