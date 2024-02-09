import os

import yt_dlp
from yt_dlp.utils import DownloadCancelled
from PyQt5.QtCore import QThread, pyqtSignal

# DownloadingThread runs yt-dlp in background to keep the GUI responsive.
# It emits progress, status, success, and error signals back to MainApp.
class DownloadingThread(QThread):
    # Signals to update GUI from the thread
    progress_changed = pyqtSignal(int)
    status_changed = pyqtSignal(str)
    details_changed = pyqtSignal(str)
    download_finished = pyqtSignal(str)
    download_failed = pyqtSignal(str)
    download_cancelled = pyqtSignal()

    def __init__(self, url, save_dir, quality, download_type="video", playlist_title=""):
        super().__init__()
        self.url = url
        self.save_dir = save_dir
        self.quality = quality
        self.download_type = download_type
        self.playlist_title = playlist_title
        self.stop_requested = False

    def Cancel_download(self):
        self.stop_requested = True

    def Format_bytes(self, byte_count):
        if byte_count is None or byte_count <= 0:
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
        if seconds is None:
            return ""

        try:
            total_seconds = int(seconds)
        except (TypeError, ValueError):
            return ""

        if total_seconds < 0:
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

    # Handle selected quality and return yt-dlp format string
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
            if "downloaded_bytes" in d:
                downloaded = d.get("downloaded_bytes", 0)

            if "total_bytes" in d:
                total_size = d["total_bytes"]
            elif "total_bytes_estimate" in d:
                total_size = d.get("total_bytes_estimate", 0)

            if total_size > 0:
                progress = int((downloaded / total_size) * 100)
                self.progress_changed.emit(progress)

            speed_value = d.get("speed")
            eta_value = d.get("eta")

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
            if total_text and downloaded_text:
                detail_parts.append(f"{downloaded_text} of {total_text}")
            elif downloaded_text:
                detail_parts.append(downloaded_text)

            if speed_text:
                detail_parts.append(f"{speed_text}/s")

            if eta_text:
                detail_parts.append(f"ETA {eta_text}")

            status_prefix = "Downloading"
            info_dict = d.get("info_dict", {})
            if self.download_type == "playlist":
                playlist_index = info_dict.get("playlist_index")
                playlist_count = info_dict.get("n_entries") or info_dict.get("playlist_count")
                if playlist_index and playlist_count:
                    status_prefix = f"Item {playlist_index} of {playlist_count}"

            self.status_changed.emit(f"{status_prefix}  {percent_value}%")
            self.details_changed.emit("   |   ".join(detail_parts) if detail_parts else "Receiving video data")

        if status == "finished":
            self.progress_changed.emit(100)
            self.status_changed.emit("Finalizing file")
            self.details_changed.emit("Merging audio and video, then saving the final file")

    def run(self):
        try:
            selected_format = self.Handle_quality_format()
            self.status_changed.emit("Preparing download")
            self.details_changed.emit("Connecting to YouTube and preparing the selected format")

            output_template = os.path.join(self.save_dir, "%(title)s.%(ext)s")
            if self.download_type == "playlist":
                playlist_folder = os.path.join(self.save_dir, self.Safe_name(self.playlist_title))
                os.makedirs(playlist_folder, exist_ok=True)
                output_template = os.path.join(playlist_folder, "%(playlist_index)03d - %(title)s.%(ext)s")

            ydl_opts = {
                "format": selected_format,
                "outtmpl": output_template,
                "noplaylist": self.download_type != "playlist",
                "progress_hooks": [self.progress_hook],
                "quiet": True,
                "no_warnings": True,
                "continuedl": True,
                "overwrites": False,
            }

            if self.download_type == "playlist":
                ydl_opts["ignoreerrors"] = True

            with yt_dlp.YoutubeDL(ydl_opts) as ydl: # pyright: ignore[reportArgumentType]
                ydl.download([self.url])

            if self.stop_requested:
                self.download_cancelled.emit()
                return

            self.download_finished.emit(self.save_dir)

        except Exception as error:
            if self.stop_requested:
                self.download_cancelled.emit()
                return

            self.download_failed.emit(str(error))
