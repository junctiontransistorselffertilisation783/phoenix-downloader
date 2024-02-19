import os
import re

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
        self.download_subtitles = download_subtitles
        self.download_chapters = download_chapters
        self.video_language = video_language
        self.stop_requested = False
        self.chapter_targets = {}

    def Cancel_download(self):
        self.stop_requested = True

    def Handle_ydl_opts(self, output_template):
        return build_download_options(
            output_template=output_template,
            quality=self.quality,
            download_type=self.download_type,
            progress_hook=self.progress_hook,
        )

    def Handle_subtitle_pass_options(self, output_template, subtitle_options):
        return build_subtitle_download_options(
            output_template=output_template,
            progress_hook=self.progress_hook,
            subtitle_options=subtitle_options,
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

            total_bytes = d.get("total_bytes")
            total_estimate = d.get("total_bytes_estimate")
            if total_bytes is not None:
                total_size = handle_num(total_bytes)
            elif total_estimate is not None:
                total_size = handle_num(total_estimate)

            if total_size > 0:
                progress = int((downloaded / total_size) * 100)
                self.progress_changed.emit(progress)

            speed_value = handle_num(d.get("speed"))
            eta_value = handle_num(d.get("eta"))

            if total_size <= 0 and downloaded > 0:
                progress = 0
                self.progress_changed.emit(progress)

            percent_value = 0
            if total_size > 0:
                percent_value = int((downloaded / total_size) * 100)

            downloaded_text = format_bytes(downloaded)
            total_text = format_bytes(total_size)
            speed_text = format_bytes(speed_value)
            eta_text = format_seconds(eta_value)

            detail_parts = []
            info_dict = d.get("info_dict", {})
            ext_value = str(info_dict.get("ext", "")).lower()
            is_subtitle_file = ext_value in ["vtt", "srt", "ttml", "sbv", "json"]
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

            self.status_changed.emit(f"{status_prefix}  {percent_value}%")
            self.details_changed.emit("   |   ".join(detail_parts) if detail_parts else "Receiving video data")

        if status == "finished":
            info_dict = d.get("info_dict", {})
            ext_value = str(info_dict.get("ext", "")).lower()
            is_subtitle_file = ext_value in ["vtt", "srt", "ttml", "sbv", "json"]
            if self.download_chapters and not is_subtitle_file:
                chapters = info_dict.get("chapters")
                output_filename = d.get("filename")
                if output_filename and isinstance(chapters, list) and len(chapters) > 0:
                    self.chapter_targets[output_filename] = chapters

            self.progress_changed.emit(100)
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

    def run(self):
        try:
            self.status_changed.emit("Preparing download")
            self.details_changed.emit("Connecting to YouTube and preparing the selected format")

            output_template = os.path.join(self.save_dir, "%(title)s.%(ext)s")
            if self.download_type == "playlist":
                playlist_folder = os.path.join(self.save_dir, safe_name(self.playlist_title))
                os.makedirs(playlist_folder, exist_ok=True)
                output_template = os.path.join(playlist_folder, "%(playlist_index)03d - %(title)s.%(ext)s")

            ydl_opts = self.Handle_ydl_opts(output_template)

            with yt_dlp.YoutubeDL(ydl_opts) as ydl: # pyright: ignore[reportArgumentType]
                ydl.download([self.url])

            if self.download_subtitles and not self.stop_requested:
                subtitle_passes = build_subtitle_passes(self.download_subtitles, self.video_language)
                subtitle_errors = []
                for subtitle_pass in subtitle_passes:
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
                    except Exception as error:
                        error_text = str(error)
                        if is_subtitle_error(error_text):
                            subtitle_errors.append(error_text)
                            continue
                        raise

                if subtitle_errors:
                    self.status_changed.emit("Download completed with subtitle warning")
                    self.details_changed.emit("Some subtitle languages failed (e.g. rate limit), video is saved")

                self.Cleanup_subtitle_orig_files(output_template)

            if self.download_chapters and not self.stop_requested:
                self.Write_chapters_files()

            if self.stop_requested:
                self.download_cancelled.emit()
                return

            self.download_finished.emit(self.save_dir)

        except Exception as error:
            if self.stop_requested:
                self.download_cancelled.emit()
                return

            self.download_failed.emit(str(error))
