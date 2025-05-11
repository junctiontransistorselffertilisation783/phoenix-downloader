import json
import logging
from datetime import datetime

from app.core.database import Get_db_connection, Init_db_tables


class AppSettingsStore:
    def __init__(self):
        Init_db_tables()
        self.logger = logging.getLogger(__name__)

    def Handle_now_text(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def Get_value(self, setting_key, default_value=""):
        key_text = str(setting_key or "").strip()
        if key_text == "":
            return default_value

        with Get_db_connection() as connection:
            cursor = connection.execute(
                "SELECT setting_value FROM app_settings WHERE setting_key = ?",
                (key_text,),
            )
            row = cursor.fetchone()

        if row is None:
            return default_value
        return str(row["setting_value"] or default_value)

    def Set_value(self, setting_key, setting_value):
        key_text = str(setting_key or "").strip()
        if key_text == "":
            return
        value_text = str(setting_value or "")
        now_text = self.Handle_now_text()

        with Get_db_connection() as connection:
            connection.execute(
                """
                INSERT INTO app_settings (setting_key, setting_value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(setting_key) DO UPDATE SET
                    setting_value = excluded.setting_value,
                    updated_at = excluded.updated_at
                """,
                (key_text, value_text, now_text),
            )
            connection.commit()

    def Get_list(self, setting_key):
        value_text = self.Get_value(setting_key, "")
        if value_text == "":
            return []
        try:
            data = json.loads(value_text)
            if isinstance(data, list):
                return data
        except Exception:
            self.logger.warning("failed to parse list setting key=%s", setting_key)
            return []
        return []

    def Set_list(self, setting_key, values):
        if not isinstance(values, list):
            values = []
        safe_values = [str(item or "") for item in values if str(item or "") != ""]
        self.Set_value(setting_key, json.dumps(safe_values, ensure_ascii=True))
