import os


APP_DIR_NAME = "PhoenixDownloader"
APP_SETTINGS_NAME = "PhoenixDownloaderApp"
TEMP_MEDIA_DIR_NAME = "temp_media"
CACHE_FILE_NAME = "download_cache.csv"
DB_FILE_NAME = "phoenix_downloader.db"
DEFAULT_DOWNLOADS_FOLDER_NAME = "Downloads"

TEMP_KEEP_DAYS = 10
TEMP_HARD_DELETE_DAYS = 30
TEMP_MAX_BYTES = 10 * 1024 * 1024 * 1024
TEMP_KEEP_FLOOR_BYTES = 800 * 1024 * 1024


def Get_local_app_data_dir():
    base_dir = os.getenv("LOCALAPPDATA", "")
    if base_dir == "":
        base_dir = os.path.expanduser("~")
    return base_dir


def Get_app_data_dir():
    app_dir = os.path.join(Get_local_app_data_dir(), APP_DIR_NAME)
    os.makedirs(app_dir, exist_ok=True)
    return app_dir


def Get_temp_media_dir():
    temp_dir = os.path.join(Get_app_data_dir(), TEMP_MEDIA_DIR_NAME)
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir


def Get_cache_file_path():
    return os.path.join(Get_app_data_dir(), CACHE_FILE_NAME)


def Get_db_file_path():
    return os.path.join(Get_app_data_dir(), DB_FILE_NAME)


def Get_default_downloads_dir():
    return os.path.join(os.path.expanduser("~"), DEFAULT_DOWNLOADS_FOLDER_NAME)
