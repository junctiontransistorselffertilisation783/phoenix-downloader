import requests
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import yt_dlp
from PyQt5.QtCore import QThread, pyqtSignal
from app.core.ytdlp import (
    build_browser_cookie_sources,
    build_playlist_info,
    build_quality_items,
    build_shared_ydl_options,
    build_video_info,
    is_authentication_required_error,
)


class DownloadInfoThread(QThread):
    vidoes_info = pyqtSignal(int, dict)
    update_Entreis = pyqtSignal(int, dict)
    info_failed = pyqtSignal(int, str)

    def __init__(self, url, url_type, request_id, enable_thumbnail=True):
        super().__init__()
        self.url = url
        self.url_type = url_type
        self.request_id = int(request_id)
        self.enable_thumbnail = bool(enable_thumbnail)
        self.stop_requested = False
        self.logger = logging.getLogger(__name__)

    def Handle_stop_request(self):
        self.stop_requested = True

    def Is_stopped(self):
        return bool(self.stop_requested)

    def Handle_video_only_url(self, url):
        url_text = str(url or "").strip()
        if url_text == "":
            return ""

        try:
            parsed = urlparse(url_text)
            query = parse_qs(parsed.query)
        except Exception:
            return url_text

        keep_query = {}
        for key in ["v", "t", "start"]:
            values = query.get(key, [])
            clean_values = [str(value).strip() for value in values if str(value).strip() != ""]
            if len(clean_values) > 0:
                keep_query[key] = clean_values

        new_query = urlencode(keep_query, doseq=True)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))

    def run(self):
        try:
            if self.Is_stopped():
                return

            ydl_opts = {
                **build_shared_ydl_options(),
                "skip_download": True,
            }
            if self.url_type == "playlist":
                videos_dict = self.Handle_playlist_info_fast()
                if self.Is_stopped():
                    return
                self.vidoes_info.emit(self.request_id, videos_dict)
                self.Handle_playlist_entries_enrich(videos_dict)
                return
            else:
                ydl_opts["noplaylist"] = True
                info_url = self.Handle_video_only_url(self.url)
                info_dict = self.Extract_info_with_retry(info_url, ydl_opts)
                videos_dict = self.Handle_video_info(info_dict)

            if self.Is_stopped():
                return
            self.vidoes_info.emit(self.request_id, videos_dict)

        except Exception as error:
            if self.Is_stopped():
                return
            self.logger.exception("failed to load video info")
            self.info_failed.emit(self.request_id, str(error))

    def Handle_video_info(self, info_dict):
        thumbnail_data = None
        thumbnail_url = info_dict.get("thumbnail", "")
        if self.enable_thumbnail and thumbnail_url:
            thumbnail_data = self.Handle_thumbnail_data(thumbnail_url)
        return build_video_info(info_dict, thumbnail_data)

    def Handle_playlist_info(self, info_dict):
        entries = info_dict.get("entries", [])
        valid_entries = [entry for entry in entries if entry]

        thumbnail_data = None
        thumbnail_url = info_dict.get("thumbnail", "")

        if (not thumbnail_url):
            thumbnails_list = info_dict.get("thumbnails", [])
            if isinstance(thumbnails_list, list) and len(thumbnails_list) > 0:
                last_thumb = thumbnails_list[-1]
                if isinstance(last_thumb, dict):
                    thumbnail_url = last_thumb.get("url", "")

        if (not thumbnail_url) and len(valid_entries) > 0:
            thumbnail_url = valid_entries[0].get("thumbnail", "")

        if self.enable_thumbnail and thumbnail_url:
            thumbnail_data = self.Handle_thumbnail_data(thumbnail_url)

        return build_playlist_info(info_dict, thumbnail_data)

    def Handle_playlist_info_fast(self):
        flat_opts = {
            **build_shared_ydl_options(),
            "skip_download": True,
            "extract_flat": "in_playlist",
        }

        flat_info = self.Extract_info_with_retry(self.url, flat_opts)

        return self.Handle_playlist_info(flat_info)

    def Handle_playlist_entries_enrich(self, playlist_data):
        if self.Is_stopped():
            return

        full_opts = {
            **build_shared_ydl_options(),
            "skip_download": True,
            "noplaylist": True,
        }

        entries = playlist_data.get("entries", [])
        if len(entries) == 0:
            return

        entry_urls = []
        for entry in entries:
            url = entry.get("webpage_url") or entry.get("url") or ""
            entry_urls.append(str(url))

        def load_one_entry(index_value, entry_url):
            if self.Is_stopped():
                return None
            if entry_url == "":
                return {"index": index_value, "quality_items": []}

            entry_info = self.Extract_info_with_retry(entry_url, full_opts)

            formats = entry_info.get("formats", [])
            duration_seconds = entry_info.get("duration", 0)
            quality_items = build_quality_items(formats, duration_seconds)
            thumbnail_data = None
            thumbnail_url = entry_info.get("thumbnail", "")
            if self.enable_thumbnail and thumbnail_url:
                thumbnail_data = self.Handle_thumbnail_data(thumbnail_url)
            return {
                "index": index_value,
                "title": str(entry_info.get("title", "")),
                "duration_seconds": duration_seconds or 0,
                "quality_items": quality_items,
                "is_available": len(quality_items) > 0,
                "thumbnail_data": thumbnail_data,
            }

        try:
            first_result = load_one_entry(1, entry_urls[0])
            if (first_result is not None) and (not self.Is_stopped()):
                self.update_Entreis.emit(self.request_id, first_result)
        except Exception:
            self.logger.warning("first playlist entry enrich failed")

        remaining = [(i + 1, entry_urls[i]) for i in range(1, len(entry_urls))]

        group_size = 3
        for group_start in range(0, len(remaining), group_size):
            if self.Is_stopped():
                return

            group_items = remaining[group_start:group_start + group_size]
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [
                    executor.submit(load_one_entry, index_value, entry_url)
                    for index_value, entry_url in group_items
                ]
                for future in as_completed(futures):
                    if self.Is_stopped():
                        return
                    try:
                        result = future.result()
                        if (result is not None) and (not self.Is_stopped()):
                            self.update_Entreis.emit(self.request_id, result)
                    except Exception:
                        self.logger.warning("playlist entry enrich failed")
                        continue

        return

    def Handle_thumbnail_data(self, thumbnail_url):
        try:
            response = requests.get(thumbnail_url, timeout=10)
            if response.status_code == 200:
                return response.content
            return None
        except Exception:
            self.logger.warning("thumbnail download failed")
            return None

    def Extract_info_with_retry(self, url, ydl_opts):
        options = dict(ydl_opts or {})
        try:
            with yt_dlp.YoutubeDL(options) as ydl: # type: ignore
                return ydl.extract_info(url, download=False)
        except Exception as error:
            if not is_authentication_required_error(error):
                raise

            last_error = error
            for cookie_source in build_browser_cookie_sources():
                if self.Is_stopped():
                    raise last_error

                retry_options = dict(options)
                retry_options["cookiesfrombrowser"] = cookie_source
                try:
                    self.logger.info("retrying yt-dlp info with browser cookies source=%s", cookie_source[0])
                    with yt_dlp.YoutubeDL(retry_options) as ydl: # type: ignore
                        return ydl.extract_info(url, download=False)
                except Exception as retry_error:
                    last_error = retry_error
                    continue

            raise last_error
