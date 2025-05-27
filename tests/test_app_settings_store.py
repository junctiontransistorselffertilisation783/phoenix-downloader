from app.repositories.app_settings_store import AppSettingsStore


def test_app_settings_store_value_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    store = AppSettingsStore()
    store.Set_value("last_folder", "C:/Downloads")

    assert store.Get_value("last_folder") == "C:/Downloads"


def test_app_settings_store_list_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    store = AppSettingsStore()
    store.Set_list("recent_urls", ["u1", "u2", "", None])

    assert store.Get_list("recent_urls") == ["u1", "u2"]
