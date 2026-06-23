import tempfile
import unittest
from pathlib import Path

from app_settings import AppSettings, SettingsStore


class SettingsStoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "nested" / "settings.json"

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_file_returns_defaults(self):
        settings = SettingsStore(self.path).load()
        self.assertEqual(settings, AppSettings())

    def test_save_then_load_round_trips(self):
        store = SettingsStore(self.path)
        store.save(AppSettings(last_port_key="sn:ABC", custom_names={"sn:ABC": "Desk Fan"}, auto_reconnect=True))

        loaded = SettingsStore(self.path).load()

        self.assertEqual(loaded.last_port_key, "sn:ABC")
        self.assertEqual(loaded.custom_names, {"sn:ABC": "Desk Fan"})
        self.assertTrue(loaded.auto_reconnect)

    def test_corrupt_file_returns_defaults(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("{not valid json", "utf-8")

        self.assertEqual(SettingsStore(self.path).load(), AppSettings())

    def test_non_dict_payload_returns_defaults(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("[1, 2, 3]", "utf-8")

        self.assertEqual(SettingsStore(self.path).load(), AppSettings())


if __name__ == "__main__":
    unittest.main()
