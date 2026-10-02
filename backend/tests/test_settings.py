import unittest
from pathlib import Path

from app.core.config import Settings


class SettingsTests(unittest.TestCase):
    def test_environment_file_stays_in_backend_root(self):
        expected = Path(__file__).resolve().parents[1] / '.env'
        self.assertEqual(Settings.model_config['env_file'], expected)
