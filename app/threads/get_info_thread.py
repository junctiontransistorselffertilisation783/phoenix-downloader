import requests

import yt_dlp
from PyQt5.QtCore import QThread, pyqtSignal
from app.utils.helpers import format_duration_unknown


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
                data = self.playlist_info(info_dict)
            else:
                data = self.video_info(info_dict)

            self.vidoes_info.emit(data)

        except Exception as error:
            self.info_failed.emit(str(error))

    def video_info(self, info_dict):
        title = str(info_dict.get("title", "Unknown title"))
        duration_seconds = info_dict.get("duration", 0)
        duration_text = format_duration_unknown(duration_seconds)
        uploader = str(info_dict.get("uploader") or info_dict.get("channel") or "Unknown channel")

        thumbnail_data = None
        thumbnail_url = info_dict.get("thumbnail", "")
        if thumbnail_url:
            thumbnail_data = self.get_thumbnail(thumbnail_url)

        formats = info_dict.get("formats", [])
        quality_items = self.Handle_quality_formats(formats, duration_seconds)

        return {
            "info_type": "video",
            "title": title,
            "uploader": uploader,
            "duration_text": duration_text,
            "thumbnail_data": thumbnail_data,
            "quality_items": quality_items,
        }

    def playlist_info(self, info_dict):
        title = str(info_dict.get("title", "Unknown playlist"))
        uploader = str(info_dict.get("uploader") or info_dict.get("channel") or info_dict.get("playlist_uploader") or "Unknown channel")
        entries = info_dict.get("entries", [])
        valid_entries = []
        total_duration_seconds = 0

        for entry in entries:
            if entry:
                valid_entries.append(entry)

        playlist_count = info_dict.get("playlist_count", len(valid_entries))
        if not playlist_count:
            playlist_count = len(valid_entries)

        thumbnail_data = None
        thumbnail_url = info_dict.get("thumbnail", "")

        if (not thumbnail_url) and len(valid_entries) > 0:
            thumbnail_url = valid_entries[0].get("thumbnail", "")

        if thumbnail_url:
            thumbnail_data = self.get_thumbnail(thumbnail_url)

        playlist_entries = []
        for i, entry in enumerate(valid_entries):
            duration_seconds = entry.get("duration", 0)
            if duration_seconds:
                total_duration_seconds += int(duration_seconds)

            entry_formats = entry.get("formats", [])
            entry_quality_items = []
            if entry_formats:
                entry_quality_items = self.Handle_quality_formats(entry_formats, duration_seconds)

            webpage_url = entry.get("webpage_url") or entry.get("url") or ""
            playlist_entries.append({
                "index": i + 1,
                "title": str(entry.get("title", f"Video {i+1}")),
                "duration_text": format_duration_unknown(duration_seconds),
                "duration_seconds": duration_seconds or 0,
                "webpage_url": str(webpage_url),
                "is_available": bool(webpage_url),
                "quality_items": entry_quality_items,
            })

        return {
            "info_type": "playlist",
            "title": title,
            "uploader": uploader,
            "playlist_count": playlist_count,
            "total_duration_text": format_duration_unknown(total_duration_seconds),
            "thumbnail_data": thumbnail_data,
            "entries": playlist_entries,
            "quality_items": self.Handle_playlist_quality_items(),
        }

    def get_thumbnail(self, thumbnail_url):
        try:
            response = requests.get(thumbnail_url, timeout=10)
            if response.status_code == 200:
                return response.content
            return None
        except Exception:
            return None

    def get_size_bytes(self, format_info, duration_seconds):
        if "filesize" in format_info and format_info["filesize"]:
            return int(format_info["filesize"])

        if "filesize_approx" in format_info and format_info["filesize_approx"]:
            return int(format_info["filesize_approx"])

        if "tbr" in format_info and format_info["tbr"] and duration_seconds:
            return int((float(format_info["tbr"]) * 1000 / 8) * float(duration_seconds))

        return 0

    def format_size(self, size_bytes):
        if size_bytes <= 0:
            return "Unknown size"
        return f"{size_bytes / (1024 * 1024):.1f} MB"

    def Handle_playlist_quality_items(self):
        return [
            {
                "label": "Best available",
                "format": "(bv[ext=mp4][container=mp4_dash]+139)/(bv[ext=mp4][container=mp4_dash]+140)/(bv[ext=mp4]+ba[ext=m4a])/best[ext=mp4]/best",
            },
            {
                "label": "1080p or lower",
                "format": "(bv[height<=1080][ext=mp4][container=mp4_dash]+139)/(bv[height<=1080][ext=mp4][container=mp4_dash]+140)/(bv[height<=1080][ext=mp4]+ba[ext=m4a])/best[height<=1080][ext=mp4]/best[height<=1080]/best",
            },
            {
                "label": "720p or lower",
                "format": "(bv[height<=720][ext=mp4][container=mp4_dash]+139)/(bv[height<=720][ext=mp4][container=mp4_dash]+140)/(bv[height<=720][ext=mp4]+ba[ext=m4a])/best[height<=720][ext=mp4]/best[height<=720]/best",
            },
            {
                "label": "480p or lower",
                "format": "(bv[height<=480][ext=mp4][container=mp4_dash]+139)/(bv[height<=480][ext=mp4][container=mp4_dash]+140)/(bv[height<=480][ext=mp4]+ba[ext=m4a])/best[height<=480][ext=mp4]/best[height<=480]/best",
            },
            {
                "label": "Audio only",
                "format": "140/139/ba[ext=m4a]/ba",
            },
        ]

    def Handle_quality_formats(self, formats, duration_seconds):
        quality_items = []
        filtered_formats = [format_info for format_info in formats if (format_info.get("ext") in ["mp4", "m4a"]) and (format_info.get("container") in ["mp4_dash", "m4a_dash"])]

        if len(filtered_formats) == 0:
            filtered_formats = [format_info for format_info in formats if (format_info.get("ext") in ["mp4", "m4a"])]

        for i, format_info in enumerate(filtered_formats):
            format_id = str(format_info.get("format_id", "N/A"))
            resolution = str(format_info.get("resolution", "N/A"))
            extenstion = str(format_info.get("ext", "N/A"))
            filesize = self.get_size_bytes(format_info, duration_seconds)
            if filesize is None:
                filesize = 0

            label = f"{i+1}. {resolution:<9} - {extenstion:<4} - {filesize/1024/1024:.3f} MB"

            acodec = str(format_info.get("acodec", "none"))
            has_audio = acodec != "none"
            height = format_info.get("height")
            format_code = ""
            
            if resolution == "audio only":
                format_code = f"{format_id}/139/140/ba[ext=m4a]/ba"
            elif has_audio:
                format_code = format_id
                label = f"{label} (video+audio)"
            else:
                if height:
                    format_code = (
                        f"({format_id}+139)/"
                        f"({format_id}+ba[ext=m4a])/"
                        f"({format_id}+ba)/"
                        f"(bv[height<={height}][ext=mp4][container=mp4_dash]+139)/"
                        f"(bv[height<={height}][ext=mp4][container=mp4_dash]+ba[ext=m4a])/"
                        f"(bv[ext=mp4][container=mp4_dash]+139)/"
                        f"(bv[ext=mp4][container=mp4_dash]+ba[ext=m4a])/"
                        f"best[ext=mp4]/best"
                    )

            quality_items.append({"label": label, "format": format_code})

        quality_items.append({
            "label": "Best",
            "format": "(bv[ext=mp4][container=mp4_dash]+139)/(bv[ext=mp4][container=mp4_dash]+140)/(bv[ext=mp4]+ba[ext=m4a])/best[ext=mp4]/best",
        })
        return quality_items
