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
    download_finished = pyqtSignal(str)
    download_failed = pyqtSignal(str)
    download_cancelled = pyqtSignal()

    def __init__(self, url, save_dir, quality):
        super().__init__()
        self.url = url
        self.save_dir = save_dir
        self.quality = quality
        self.stop_requested = False

    def Cancel_download(self):
        self.stop_requested = True

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
        percent_text = ""
        speed_text = ""
        
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

            if "_percent_str" in d:
                percent_text = str(d.get("_percent_str", "")).strip()

            if "_speed_str" in d:
                speed_text = str(d.get("_speed_str", "")).strip()

            if percent_text and speed_text:
                self.status_changed.emit(f"Downloading {percent_text} at {speed_text}")
            elif percent_text:
                self.status_changed.emit(f"Downloading {percent_text}")
            else:
                self.status_changed.emit("Downloading...")
        if status == "finished":
            self.progress_changed.emit(100)
            self.status_changed.emit("Finalizing file...")

    def run(self):
        try:
            selected_format = self.Handle_quality_format()

            ydl_opts = {
                "format": selected_format,
                "outtmpl": os.path.join(self.save_dir, "%(title)s.%(ext)s"),
                "noplaylist": True,
                "progress_hooks": [self.progress_hook],
                "quiet": True,
                "no_warnings": True,
            }

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
