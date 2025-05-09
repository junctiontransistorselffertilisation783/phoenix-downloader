import os
import threading
import hashlib
import logging
from urllib.parse import parse_qs, urlparse

import yt_dlp
from yt_dlp.utils import DownloadCancelled
from PyQt5.QtCore import QThread, pyqtSignal
from app.models.download_job import DownloadJob
from app.config import Get_temp_media_dir
from app.services.download_files_service import DownloadFilesService
from app.utils.helpers import (
    build_playlist_prefix_template,
    build_suffix_text,
    handle_num,
    format_bytes,
    format_seconds,
    is_subtitle_file as check_subtitle_file,
    safe_name,
)
from app.core.ytdlp import (
    build_download_options,
    build_subtitle_download_options,
    build_subtitle_passes,
    compute_combined_progress,
    get_progress_item_key,
    get_progress_stream_key,
    get_progress_stream_size,
    is_subtitle_error,
)

class DownloadingThread(QThread):
    progress_changed = pyqtSignal(int)
    status_changed = pyqtSignal(str)
    details_changed = pyqtSignal(str)
    title_changed = pyqtSignal(str)
    download_finished = pyqtSignal(str)
    download_failed = pyqtSignal(str)
    download_cancelled = pyqtSignal()
    files_copied = pyqtSignal(object)
    cache_progress = pyqtSignal(object)

    def __init__(self, job: DownloadJob):
        super().__init__()
        self.job = job
        self.url = str(job.url or "")
        self.save_dir = str(job.save_dir or "")
        self.quality = str(job.quality or "")
        self.download_type = str(job.download_type or "video")
        self.playlist_title = str(job.playlist_title or "")
        self.playlist_count = int(job.playlist_count or 0)
        self.playlist_selected_count = int(job.playlist_selected_count or 0)
        self.playlist_items = str(job.playlist_items or "").strip()
        self.add_prefix = bool(job.add_prefix)
        self.prefix_mode = int(job.prefix_mode or 0)
        self.add_suffix = bool(job.add_suffix)
        self.suffix_text = str(job.suffix_text or "")
        self.download_subtitles = bool(job.download_subtitles)
        self.download_chapters = bool(job.download_chapters)
        self.video_language = str(job.video_language or "")
        self.stop_requested = False
        self.chapter_targets = {}
        self.subtitle_thread = None
        self.subtitle_errors = []
        self.subtitle_fatal_error = None
        self.chapter_thread = None
        self.output_template = ""
        self.media_progress_state = {}
        self.last_global_progress = 0
        self.completed_output_files = []
        self.temp_work_dir = ""
        self.last_cache_emit = {}
        self.download_files_service = DownloadFilesService()
        self.logger = logging.getLogger(__name__)

    def Cancel_download(self):
        self.stop_requested = True

    def Ensure_item_state(self, info_dict):
        item_key = get_progress_item_key(info_dict)
        if item_key in self.media_progress_state:
            return item_key, self.media_progress_state[item_key]

        duration_seconds = handle_num(info_dict.get("duration"))
        expected_total = 0
        requested_formats = info_dict.get("requested_formats", [])
        if isinstance(requested_formats, list) and len(requested_formats) > 0:
            for stream_info in requested_formats:
                expected_total += get_progress_stream_size(stream_info, duration_seconds)
        else:
            expected_total = get_progress_stream_size(info_dict, duration_seconds)

        self.media_progress_state[item_key] = {
            "expected_total": expected_total,
            "runtime_total": 0,
            "stream_totals": {},
            "stream_downloaded": {},
            "last_percent": 0,
        }
        return item_key, self.media_progress_state[item_key]

    def Handle_ydl_opts(self, output_template):
        return build_download_options(
            output_template=output_template,
            quality=self.quality,
            download_type=self.download_type,
            progress_hook=self.progress_hook,
            playlist_items=self.playlist_items,
            download_subtitles=self.download_subtitles,
            video_language=self.video_language,
        )

    def Handle_subtitle_pass_options(self, output_template, subtitle_options):
        return build_subtitle_download_options(
            output_template=output_template,
            progress_hook=self.progress_hook,
            subtitle_options=subtitle_options,
            download_type=self.download_type,
            playlist_items=self.playlist_items,
        )

    def Handle_cache_emit(self, info_dict, status_text, temp_file, downloaded, total_size, progress_value):
        if not isinstance(info_dict, dict):
            return

        video_id = str(info_dict.get("id", "")).strip()
        playlist_item = str(info_dict.get("playlist_index", "")).strip()
        cache_key = f"{video_id}|{playlist_item}|{status_text}"
        last_value = self.last_cache_emit.get(cache_key, -1)
        if last_value == int(progress_value):
            return

        self.last_cache_emit[cache_key] = int(progress_value)
        self.cache_progress.emit(
            {
                "video_id": video_id,
                "playlist_item": playlist_item,
                "state": str(status_text or ""),
                "temp_dir": str(self.temp_work_dir or ""),
                "temp_file": str(temp_file or ""),
                "bytes_downloaded": str(handle_num(downloaded)),
                "bytes_total": str(handle_num(total_size)),
                "last_progress": str(int(progress_value or 0)),
            }
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
            is_subtitle_file = check_subtitle_file(info_dict)
            temp_file = d.get("tmpfilename") or d.get("filename") or ""

            total_bytes = d.get("total_bytes")
            total_estimate = d.get("total_bytes_estimate")
            if total_bytes is not None:
                total_size = handle_num(total_bytes)
            elif total_estimate is not None:
                total_size = handle_num(total_estimate)

            if not is_subtitle_file:
                stream_key = get_progress_stream_key(info_dict)
                _item_key, item_state = self.Ensure_item_state(info_dict)
                percent_value, downloaded_combined, total_combined = compute_combined_progress(
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
                    status_prefix = f"Video {playlist_index}/{playlist_count}"

            title_text = str(info_dict.get("title", "")).strip()
            if title_text and not is_subtitle_file:
                self.title_changed.emit(title_text)

            if is_subtitle_file:
                detail_parts.insert(0, "Subtitle file")

            if not is_subtitle_file:
                self.status_changed.emit(f"{status_prefix}  {percent_value}%")
                self.Handle_cache_emit(info_dict, "downloading", temp_file, downloaded, total_size, percent_value)
            self.details_changed.emit("   |   ".join(detail_parts) if detail_parts else "Receiving video data")

        if status == "finished":
            info_dict = d.get("info_dict", {})
            is_subtitle_file = check_subtitle_file(info_dict)
            output_filename = d.get("filename")

            if (not is_subtitle_file) and output_filename:
                output_name = str(output_filename)
                exists_before = False
                for item in self.completed_output_files:
                    if str(item.get("source_file", "")) == output_name:
                        exists_before = True
                        break
                if not exists_before:
                    self.completed_output_files.append(
                        {
                            "source_file": output_name,
                            "video_id": str(info_dict.get("id", "")).strip(),
                            "playlist_item": str(info_dict.get("playlist_index", "")).strip(),
                            "title": str(info_dict.get("title", "")).strip(),
                        }
                    )

            if self.download_chapters and not is_subtitle_file:
                chapters = info_dict.get("chapters")
                if output_filename and isinstance(chapters, list) and len(chapters) > 0:
                    self.chapter_targets[output_filename] = chapters

            if not is_subtitle_file:
                if self.last_global_progress < 99:
                    self.last_global_progress = 99
                self.progress_changed.emit(self.last_global_progress)
                self.status_changed.emit("Finalizing file")
                title_text = str(info_dict.get("title", "")).strip()
                if title_text != "":
                    self.title_changed.emit(title_text)
                self.details_changed.emit("Merging audio and video, then saving the final file")
                self.Handle_cache_emit(info_dict, "downloading", output_filename, 0, 0, self.last_global_progress)

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
            self.logger.info("subtitle pass start: %s", pass_name)
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
                self.logger.info("subtitle pass cancelled")
                return
            except Exception as error:
                error_text = str(error)
                if is_subtitle_error(error_text):
                    self.subtitle_errors.append(error_text)
                    self.logger.info("subtitle optional error: %s", error_text)
                    continue
                self.subtitle_fatal_error = error
                self.logger.warning("subtitle fatal error: %s", error_text)
                return

        self.download_files_service.Cleanup_subtitle_orig_files(output_template)

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
            written_count = self.download_files_service.Write_chapters_files(self.chapter_targets)
            if written_count > 0:
                self.status_changed.emit("Chapters files created")
                self.details_changed.emit(f"Created {written_count} PotPlayer chapter file(s)")
        except Exception:
            return

    def run(self):
        try:
            self.logger.info("download thread started type=%s", self.download_type)
            self.status_changed.emit("Preparing download")
            self.details_changed.emit("Connecting to YouTube and preparing the selected format")

            os.makedirs(self.save_dir, exist_ok=True)
            temp_root = Get_temp_media_dir()

            video_id = ""
            try:
                parsed = urlparse(str(self.url or ""))
                query = parse_qs(parsed.query)
                if "v" in query and len(query["v"]) > 0:
                    video_id = str(query["v"][0]).strip()
                if video_id == "":
                    host = str(parsed.netloc or "").lower()
                    path_value = str(parsed.path or "").strip("/")
                    if "youtu.be" in host:
                        video_id = path_value
            except Exception:
                video_id = ""

            key_text = f"{self.url}|{self.download_type}|{self.quality}|{self.playlist_items}"
            key_hash = hashlib.sha1(key_text.encode("utf-8")).hexdigest()[:12]
            if video_id != "":
                temp_folder_name = f"{video_id}_{key_hash}"
            else:
                temp_folder_name = f"job_{key_hash}"

            temp_work_dir = os.path.join(temp_root, temp_folder_name)
            os.makedirs(temp_work_dir, exist_ok=True)
            self.temp_work_dir = temp_work_dir

            suffix_text = build_suffix_text(self.add_suffix, self.suffix_text)
            if self.download_type == "playlist":
                folder_title = safe_name(self.playlist_title)
                if self.playlist_count > 0:
                    folder_title = f"{folder_title} [ {self.playlist_count} ]"

                target_playlist_folder = os.path.join(self.save_dir, folder_title)
                temp_playlist_folder = os.path.join(temp_work_dir, folder_title)
                os.makedirs(target_playlist_folder, exist_ok=True)
                os.makedirs(temp_playlist_folder, exist_ok=True)

                prefix_template = build_playlist_prefix_template(
                    self.add_prefix,
                    self.prefix_mode,
                    self.playlist_count,
                    self.playlist_selected_count,
                )
                temp_output_template = os.path.join(temp_playlist_folder, f"{prefix_template}%(title)s{suffix_text}.%(ext)s")
            else:
                temp_output_template = os.path.join(temp_work_dir, f"%(title)s{suffix_text}.%(ext)s")

            self.output_template = temp_output_template
            ydl_opts = self.Handle_ydl_opts(temp_output_template)

            self.status_changed.emit("Preparing temp workspace")
            self.details_changed.emit("Using AppData temp cache for .part resume")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl: # pyright: ignore[reportArgumentType]
                ydl.download([self.url])

            if self.download_subtitles:
                self.download_files_service.Cleanup_subtitle_orig_files(temp_output_template)

            self.status_changed.emit("Copying final files")
            copied_count, removed_temp_count, copied_relative_files = self.download_files_service.Handle_copy_final_files(
                temp_work_dir,
                self.save_dir,
                self.completed_output_files,
            )

            if copied_count > 0:
                self.files_copied.emit(copied_relative_files)
                self.details_changed.emit(f"Moved {copied_count} file(s) to target and cleared {removed_temp_count} temp file(s)")
                self.logger.info("copied files=%s removed_temp=%s", copied_count, removed_temp_count)
            else:
                self.files_copied.emit([])
                self.details_changed.emit("No new files copied (already exists in target or still partial)")
                self.logger.info("no files copied from temp workspace")

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
            self.logger.info("download finished save_dir=%s", self.save_dir)

            self.Handle_cleanup_temp_cache(self.temp_work_dir)

        except Exception as error:
            if self.stop_requested:
                self.download_cancelled.emit()
                self.Handle_cleanup_temp_cache(self.temp_work_dir)
                self.logger.info("download cancelled while handling exception")
                return

            self.download_failed.emit(str(error))
            self.Handle_cleanup_temp_cache(self.temp_work_dir)
            self.logger.exception("download thread failed")

    def Handle_cleanup_temp_cache(self, active_temp_dir=""):
        self.download_files_service.Handle_cleanup_temp_cache(active_temp_dir)
