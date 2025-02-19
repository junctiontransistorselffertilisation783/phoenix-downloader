import sqlite3

from app.config import Get_db_file_path


def Get_db_connection():
    db_path = Get_db_file_path()
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def Init_db_tables():
    with Get_db_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS download_state (
                cache_key TEXT PRIMARY KEY,
                video_id TEXT NOT NULL DEFAULT '',
                list_id TEXT NOT NULL DEFAULT '',
                download_type TEXT NOT NULL DEFAULT '',
                playlist_item TEXT NOT NULL DEFAULT '',
                playlist_items TEXT NOT NULL DEFAULT '',
                format_simple TEXT NOT NULL DEFAULT '',
                format_raw TEXT NOT NULL DEFAULT '',
                state TEXT NOT NULL DEFAULT '',
                temp_dir TEXT NOT NULL DEFAULT '',
                temp_file TEXT NOT NULL DEFAULT '',
                target_dir TEXT NOT NULL DEFAULT '',
                target_name TEXT NOT NULL DEFAULT '',
                bytes_downloaded INTEGER NOT NULL DEFAULT 0,
                bytes_total INTEGER NOT NULL DEFAULT 0,
                last_progress INTEGER NOT NULL DEFAULT 0,
                last_error TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT '',
                state_changed_at TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_download_state_state ON download_state(state)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_download_state_temp_dir ON download_state(temp_dir)")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        connection.commit()
