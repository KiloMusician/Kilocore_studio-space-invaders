from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from space_invaders.storage import load_high_score, save_high_score


class StorageTests(unittest.TestCase):
    def test_high_score_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "state" / "data.json"
            result = save_high_score(3044, path)
            self.assertEqual(result, path)
            self.assertEqual(load_high_score(path), 3044)

    def test_corrupt_file_falls_back_without_destroying_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "data.json"
            path.write_text("{not-json", encoding="utf-8")
            self.assertEqual(load_high_score(path, bundled_default=17), 17)
            self.assertEqual(path.read_text(encoding="utf-8"), "{not-json")


if __name__ == "__main__":
    unittest.main()
