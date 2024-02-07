import requests

import yt_dlp
from PyQt5.QtCore import QThread, pyqtSignal


# DownloadInfoThread extracts video info before downloading.
# It sends title, duration, thumbnail bytes, and available quality options to MainApp.
class DownloadInfoThread(QThread):
    vidoes_info = pyqtSignal(dict)
    info_failed = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            ydl_opts = {
                "quiet": True,
                "skip_download": True,
                "no_warnings": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl: # type: ignore
                info_dict = ydl.extract_info(self.url, download=False)
            # print(info_dict) # for test or debug
            # get the video info
            data = self.video_info(info_dict)
            self.vidoes_info.emit(data)

        except Exception as error:
            self.info_failed.emit(str(error))

    def video_info(self, info_dict):
        # get teh title and duration
        title = str(info_dict.get("title", "Unknown title"))
        duration_seconds = info_dict.get("duration", 0)
        duration_text = self.format_duration(duration_seconds)

        # get the thumbnail
        thumbnail_data = None
        thumbnail_url = info_dict.get("thumbnail", "")
        if thumbnail_url:
            thumbnail_data = self.get_thumbnail(thumbnail_url)

        formats = info_dict.get("formats", [])
        quality_items = self.Handle_quality_formats(formats, duration_seconds)

        return {
            "title": title,
            "duration_text": duration_text,
            "thumbnail_data": thumbnail_data,
            "quality_items": quality_items,
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
            # tbr is in Kbits/s
            return int((float(format_info["tbr"]) * 1000 / 8) * float(duration_seconds))

        return 0

    def format_size(self, size_bytes):
        if size_bytes <= 0:
            return "Unknown size"
        return f"{size_bytes / (1024 * 1024):.1f} MB"

    def format_duration(self, seconds):
        try:
            total = int(seconds)
        except Exception:
            total = 0

        if total <= 0:
            return "Unknown"

        hours = total // 3600
        minutes = (total % 3600) // 60
        # secs = total - (hours * 3600 )+( minutes & 60 ) 
        secs = total % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    # Method to handle appearing the Quality_comboBox data with available video qualities
    def Handle_quality_formats(self, formats, duration_seconds):
        quality_items = []
        # Filter formats to include only mp4 and m4a with dash containers 
        filtered_formats = [format_info for format_info in formats if (format_info.get("ext") in ["mp4", "m4a"]) and (format_info.get("container") in ["mp4_dash", "m4a_dash"])]

        # fallback when container key is missing in some extractors
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

            # Build download format code (close to old Handle_options style)
            acodec = str(format_info.get("acodec", "none"))
            has_audio = acodec != "none"
            height = format_info.get("height")
            format_code = ""
            
            # audio-only  
            if resolution == "audio only":
                format_code = f"{format_id}/139/140/ba[ext=m4a]/ba"
            # full video row already has audio (progressive)
            elif has_audio:
                format_code = format_id
                label = f"{label} (video+audio)"
            #  merge selected video with preferred audio chain
            else:
                if height:
                    # try selected id first, then nearest mp4 dash with same/lower height
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

        # always add stable presets 
        quality_items.append({
            "label": "Best",
            "format": "(bv[ext=mp4][container=mp4_dash]+139)/(bv[ext=mp4][container=mp4_dash]+140)/(bv[ext=mp4]+ba[ext=m4a])/best[ext=mp4]/best",
        })
        return quality_items
