import os

import yt_dlp
from yt_dlp.utils import DownloadCancelled
from PyQt5.QtCore import QThread, pyqtSignal

class DownloadingThread(QThread):
    progress_changed = pyqtSignal(int)
    status_changed = pyqtSignal(str)
    details_changed = pyqtSignal(str)
    download_finished = pyqtSignal(str)
    download_failed = pyqtSignal(str)
    download_cancelled = pyqtSignal()

    def __init__(self, url, save_dir, quality, download_type="video", playlist_title="", download_subtitles=False):
        super().__init__()
        self.url = url
        self.save_dir = save_dir
        self.quality = quality
        self.download_type = download_type
        self.playlist_title = playlist_title
        self.download_subtitles = download_subtitles
        self.stop_requested = False

    def Cancel_download(self):
        self.stop_requested = True

    def Handle_num(self, value):
        if value is None:
            return 0

        try:
            number_value = float(value)
        except (TypeError, ValueError):
            return 0

        if number_value < 0:
            return 0

        return number_value

    def Format_bytes(self, byte_count):
        byte_count = self.Handle_num(byte_count)
        if byte_count <= 0:
            return ""

        units = ["B", "KB", "MB", "GB"]
        value = float(byte_count)

        for unit in units:
            if value < 1024 or unit == units[-1]:
                if unit == "B":
                    return f"{int(value)} {unit}"
                return f"{value:.1f} {unit}"
            value /= 1024

        return ""

    def Format_seconds(self, seconds):
        total_seconds = int(self.Handle_num(seconds))
        if total_seconds <= 0:
            return ""

        minutes, secs = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"

        return f"{minutes:02d}:{secs:02d}"

    def Safe_name(self, text):
        cleaned = str(text).strip()
        for char in '<>:"/\\|?*':
            cleaned = cleaned.replace(char, "_")

        cleaned = " ".join(cleaned.split())
        if cleaned == "":
            return "playlist"

        return cleaned

    def Handle_subtitle_opts(self):
        if not self.download_subtitles:
            return {}

        return {
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en", "ar"],
            "subtitlesformat": "srt/best",
            "sleep_subtitles": 2,
            "postprocessors": [{
                "key": "FFmpegEmbedSubtitle",
            }],
        }

    def Handle_ydl_opts(self, output_template, use_subtitles):
        ydl_opts = {
            "format": self.Handle_quality_format(),
            "outtmpl": output_template,
            "noplaylist": self.download_type != "playlist",
            "progress_hooks": [self.progress_hook],
            "quiet": True,
            "no_warnings": True,
            "continuedl": True,
            "overwrites": False,
        }

        if use_subtitles:
            ydl_opts.update(self.Handle_subtitle_opts())

        if self.download_type == "playlist":
            ydl_opts["ignoreerrors"] = True

        return ydl_opts

    def Handle_subtitle_error(self, error_text):
        error_text = str(error_text).lower()
        subtitle_words = [
            "subtitle",
            "subtitles",
            "automatic captions",
            "requested format not available",
            "unable to download video subtitles",
        ]
        return any(word in error_text for word in subtitle_words)

    def Handle_quality_format(self):
        if ("+" in self.quality) or ("/" in self.quality) or ("[" in self.quality):
            return self.quality

        if self.quality == "Audio only (139)":
            return "139/ba[ext=m4a]"

        if self.quality == "240p":
            resolution = "240"
        elif self.quality == "480p":
            resolution = "480"
        elif self.quality == "720p":
            resolution = "720"
        else:
            resolution = ""

        if resolution != "":
            return (
                f"(bv[height<={resolution}][ext=mp4][container=mp4_dash]+139)/"
                f"(bv[height<={resolution}][ext=mp4][container=mp4_dash]+ba[ext=m4a])/"
                f"best[height<={resolution}][ext=mp4]/best"
            )

        return "(bv[ext=mp4][container=mp4_dash]+139)/(bv[ext=mp4]+ba[ext=m4a])/best[ext=mp4]/best"

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
            downloaded = self.Handle_num(d.get("downloaded_bytes", 0))

            total_bytes = d.get("total_bytes")
            total_estimate = d.get("total_bytes_estimate")
            if total_bytes is not None:
                total_size = self.Handle_num(total_bytes)
            elif total_estimate is not None:
                total_size = self.Handle_num(total_estimate)

            if total_size > 0:
                progress = int((downloaded / total_size) * 100)
                self.progress_changed.emit(progress)

            speed_value = self.Handle_num(d.get("speed"))
            eta_value = self.Handle_num(d.get("eta"))

            if total_size <= 0 and downloaded > 0:
                progress = 0
                self.progress_changed.emit(progress)

            percent_value = 0
            if total_size > 0:
                percent_value = int((downloaded / total_size) * 100)

            downloaded_text = self.Format_bytes(downloaded)
            total_text = self.Format_bytes(total_size)
            speed_text = self.Format_bytes(speed_value)
            eta_text = self.Format_seconds(eta_value)

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
            self.progress_changed.emit(100)
            self.status_changed.emit("Finalizing file")
            self.details_changed.emit("Merging audio and video, then saving the final file")

    def run(self):
        try:
            self.status_changed.emit("Preparing download")
            self.details_changed.emit("Connecting to YouTube and preparing the selected format")

            output_template = os.path.join(self.save_dir, "%(title)s.%(ext)s")
            if self.download_type == "playlist":
                playlist_folder = os.path.join(self.save_dir, self.Safe_name(self.playlist_title))
                os.makedirs(playlist_folder, exist_ok=True)
                output_template = os.path.join(playlist_folder, "%(playlist_index)03d - %(title)s.%(ext)s")

            ydl_opts = self.Handle_ydl_opts(output_template, self.download_subtitles)

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl: # pyright: ignore[reportArgumentType]
                    ydl.download([self.url])
            except Exception as error:
                if self.download_subtitles and self.Handle_subtitle_error(str(error)):
                    self.status_changed.emit("Retrying without subtitles")
                    self.details_changed.emit("Subtitle failed, video will continue")
                    retry_opts = self.Handle_ydl_opts(output_template, False)
                    with yt_dlp.YoutubeDL(retry_opts) as ydl: # pyright: ignore[reportArgumentType]
                        ydl.download([self.url])
                else:
                    raise

            if self.stop_requested:
                self.download_cancelled.emit()
                return

            self.download_finished.emit(self.save_dir)

        except Exception as error:
            if self.stop_requested:
                self.download_cancelled.emit()
                return

            self.download_failed.emit(str(error))
