
import tempfile
import unittest
from pathlib import Path

from scanner import scan_repository


class TestScanner(unittest.TestCase):
    def test_scans_source_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "main.py").write_text(
                "print('Hello')", encoding="utf-8"
            )

            files = scan_repository(str(root))

            self.assertEqual(len(files), 1)
            self.assertEqual(files[0]["path"], "main.py")
            self.assertEqual(files[0]["content"], "print('Hello')")

    def test_skips_env_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".env").write_text(
                "API_KEY=secret", encoding="utf-8"
            )

            files = scan_repository(str(root))

            self.assertEqual(files, [])

    def test_skips_venv_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            venv = root / ".venv"
            venv.mkdir()
            (venv / "hidden.py").write_text(
                "secret", encoding="utf-8"
            )

            files = scan_repository(str(root))

            self.assertEqual(files, [])


if __name__ == "__main__":
    unittest.main()
