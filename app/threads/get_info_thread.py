import requests

import yt_dlp
from PyQt5.QtCore import QThread, pyqtSignal
from app.ytdlp.core import build_playlist_info, build_video_info


class DownloadInfoThread(QThread):
    vidoes_info = pyqtSignal(dict)
    info_failed = pyqtSignal(str)

    def __init__(self, url, url_type):
        super().__init__()
        self.url = url
        self.url_type = url_type

    def run(self):
        try:
            ydl_opts = {
                "quiet": True,
                "skip_download": True,
                "no_warnings": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl: # type: ignore
                info_dict = ydl.extract_info(self.url, download=False)

            if self.url_type == "playlist":
                videos_dict = self.playlist_info(info_dict)
            else:
                videos_dict = self.video_info(info_dict)

            self.vidoes_info.emit(videos_dict)

        except Exception as error:
            self.info_failed.emit(str(error))

    def video_info(self, info_dict):
        thumbnail_data = None
        thumbnail_url = info_dict.get("thumbnail", "")
        if thumbnail_url:
            thumbnail_data = self.get_thumbnail(thumbnail_url)
        return build_video_info(info_dict, thumbnail_data)

    def playlist_info(self, info_dict):
        entries = info_dict.get("entries", [])
        valid_entries = []

        for entry in entries:
            if entry:
                valid_entries.append(entry)

        thumbnail_data = None
        thumbnail_url = info_dict.get("thumbnail", "")

        if (not thumbnail_url) and len(valid_entries) > 0:
            thumbnail_url = valid_entries[0].get("thumbnail", "")

        if thumbnail_url:
            thumbnail_data = self.get_thumbnail(thumbnail_url)

        return build_playlist_info(info_dict, thumbnail_data)

    def get_thumbnail(self, thumbnail_url):
        try:
            response = requests.get(thumbnail_url, timeout=10)
            if response.status_code == 200:
                return response.content
            return None
        except Exception:
            return None
